from __future__ import annotations
from typing import Any, Optional, Tuple, List
import os
from math import ceil
from pathlib import Path
import shutil
from PIL import Image
from . import utils
from .typealiases import Color, OptionalSize, AsciifierException, MagickException, FFmpegException


__all__ = ['CoreAsciifier', 'Magick', 'FFmpeg']


ffmpeg = 'ffmpeg'
ffprobe = 'ffprobe'
convert = 'convert'
identify = 'identify'


class PossiblyDynamic:
    """A class that wraps some CoreAsciifier parameters in order to support both callables and hard-coded values.
    To access a value, use param[frame] if dynamic. For hard-coded use param[None]."""

    def __init__(
            self, func_or_value: Any, frame_count: Optional[int],
            color_type: bool = False, reverse: bool = False) -> None:

        self.is_dynamic = callable(func_or_value)
        if self.is_dynamic:
            if frame_count is None:
                raise AsciifierException(
                    'No frame count was given in order to pre-calculate dynamic parameters.')
            # All values for every frame need to be calculated previously, instead of just saving the callable,
            # because pickling functions is not possible in multiprocessing.
            self.value = [func_or_value(i) for i in range(1, frame_count + 1)]
        else:
            self.value = func_or_value
        self.color_type = color_type
        self.reverse = reverse

    def __getitem__(self, frame: Optional[int]) -> Any:
        if self.is_dynamic:
            try:
                resp = self.value[frame - 1]
            except TypeError:
                raise AsciifierException(
                    'Frame was not specified for dynamic parameter.')
        else:
            resp = self.value
        if self.color_type and isinstance(resp, int):
            return resp, resp, resp
        if self.reverse:
            return resp[::-1]
        return resp


class CoreAsciifier:
    """The class behind all of the asciipixels functions. The main purpose of this class is to avoid repeating
    unnecessary code. Methods are used instead of helper functions to avoid passing parameters around. This class
    can be used by the user for a more specific control of the ascii art generation.

    This class is meant to be used inside a ``with`` block, in either of the following ways:

        >>> with CoreAsciifier('foo.png') as core:
        ...     core.dimensions
        (1400, 800)

        >>> core = CoreAsciifier('foo.png')
        >>> with core:
        ...     core.dimensions
        (1400, 800)
    """

    def __init__(
            self, path: str, bg: Color = 30, txt: Color = 255, definition: int = 100, out_width: OptionalSize = None,
            strict_out_dimensions: bool = False, correction: Optional[float] = None, chars: str = " .:-=+*$@#",
            reverse_chars: bool = False, frame_count: Optional[int] = None, fps: Optional[int] = None) -> None:

        """**Initialize the CoreAsciifier class.**

        :param path: The path to the image file.
        :param bg: Dynamic-compatible. The color of the background as tuple or integer (0-255). Defaults to dark
            gray (30).
        :param txt: Dynamic-compatible. The color of the ascii overlay as tuple or integer (0-255). Defaults to
            white (255).
        :param definition: Dynamic-compatible. The number of characters in the horizontal axis. Defaults to 100.
        :param out_width: The pixel width of the new image, or pass a tuple for width and height.
            In that case, width is prioritized when creating the image. Defaults to approximate input image dimensions.
        :param strict_out_dimensions: Set to True to use the exact specified output dimensions. Defaults to False.
        :param correction: Dynamic-compatible. The factor of compensation for the non-square nature of an ascii
            character. A value between zero and one shrinks the input image height. This is generally what we want.
            Defaults to approximate original proportions.
        :param chars: Dynamic-compatible. The string of characters to be used in the ascii art. Any length is accepted,
            but the characters should be in dimmest to brightest order. Defaults to ' .:-=+*$@#'
        :param reverse_chars: Whether to reverse the chars order, in case it's dark text on light background.
            Defaults to False.
        :param frame_count: The total amount of frames to generate. This is automatic for video, but must be
            specified when dynamically asciifying an image.
        :param fps: The FPS of the result gif or video. This is automatic for video, but must be
            specified when dynamically asciifying an image.
        :return: ``None``.
        """

        self.str_path = path
        self.path = Path(path)
        self.is_video = self.path.suffix[1:].lower() in ['mp4', 'mov', 'm4v', 'webm', 'avi']

        if not self.path.exists():
            raise FileNotFoundError(f'The file path \'{self.str_path}\' does not exist.')

        if self.is_video:
            self.frame_count = FFmpeg.frame_count(self.str_path)
            self.fps = FFmpeg.fps(self.str_path)
            self.dimensions = FFmpeg.dimensions(self.str_path)
        else:
            self.frame_count = frame_count
            self.fps = fps
            self.dimensions = Magick.dimensions(self.str_path)

        self.ratio = self.dimensions[1] / self.dimensions[0]
        self.strict_out_dimensions = strict_out_dimensions

        if isinstance(out_width, tuple):
            self.out_dimensions = out_width
        else:
            out_width = out_width or self.dimensions[0]
            self.out_dimensions = (out_width, int(out_width * self.ratio))

        self.bg = PossiblyDynamic(bg, self.frame_count, color_type=True)
        self.txt = PossiblyDynamic(txt, self.frame_count, color_type=True)
        self.definition = PossiblyDynamic(definition, self.frame_count)
        self.correction = PossiblyDynamic(correction, self.frame_count)
        self.chars = PossiblyDynamic(chars, self.frame_count, reverse=reverse_chars)

        self.ascii_art = ''
        self.definition_height = None
        self.text_size = None

        self.process_dir = self.path.parent / 'asciipixels'
        self.process_dir.mkdir(exist_ok=True)
        (self.process_dir / 'Frames').mkdir(exist_ok=True)
        (self.process_dir / 'NewFrames').mkdir(exist_ok=True)

    def __enter__(self) -> CoreAsciifier:
        return self

    def __exit__(self, *args: Any) -> None:
        self.remove_process_dir()
        os.environ['ASCIIPIXELS_PROCESS'] = '0'

    def figure_out_sizes(self, frame: Optional[int] = None, fine_tune: bool = True, even_sizes: bool = False) -> None:
        """Setup before making the canvas, or generating and drawing the Ascii. Finds the best values for the text
        point size, and the dimensions of the output image.

        :param frame: The frame number, if working with videos/gifs.
        :param fine_tune: Fine-tune the output dimensions so the bounds of the drawn text fit exactly. This needs to
            be set to ``False`` whenever you are recalculating sizes on different frames of a video/gif, so the
            dimensions of all frames are the same.
        :param even_sizes: Set to ``True`` whenever handling videos/gifs. FFmpeg needs even-numbered dimensions when
            converting frames to video.
        :return: ``None``.
        """

        definition = self.definition[frame]
        correction = self.correction[frame]
        # I'm not 100% sure this calculation works always.
        self.text_size = int(ceil((self.out_dimensions[0] * 1.7) / definition))

        # Test by drawing a square (definition x definition) of Ascii in the image to see how much it
        # is distorted. Compensate this distortion: self.definition_height is not just definition * ratio.
        if correction is None:
            txt_w, txt_h = Magick.text_dimensions(
                definition, definition, self.text_size,
                int(self.out_dimensions[0] * 1.5), int(self.out_dimensions[0] * 2))
            correction = txt_w / txt_h

        self.definition_height = int(definition * self.ratio * correction)

        if self.strict_out_dimensions or not fine_tune:
            return

        # Test the actual dimensions of the text that will be drawn (definition x definition_height).
        # Then reduce the output dimensions to prevent blank spaces in the bottom & right.
        txt_w, txt_h = Magick.text_dimensions(
            definition, self.definition_height, self.text_size,
            int(self.out_dimensions[0] * 1.5), int(self.out_dimensions[1] * 2))

        if even_sizes:
            self.out_dimensions = (int(txt_w * 0.5) * 2, int(txt_h * 0.5) * 2)
        else:
            self.out_dimensions = (int(txt_w), int(txt_h))

    def generate_canvas(self, frame: Optional[int] = None) -> str:
        """Generate the canvas image and save it in the process dir.

        :param frame: The frame number, if working with videos/gifs.
        :return: The path of the generated image.
        """
        canvas_path = str(self.process_dir / 'canvas.png')
        Magick.blank_png(canvas_path, *self.out_dimensions, *self.bg[frame])
        return canvas_path

    def generate_ascii_art(self, frame: Optional[int] = None) -> str:
        """Resizes the image to definition x definition_height, converts it to graydefinition and
        generates the ascii art. Uses PIL to get the pixel data.

        :param frame: The frame number, if working with videos/gifs.
        :return: The generated ascii art as a string.
        """
        if self.is_video and frame is None:
            raise AsciifierException(
                'Frame was not specified for ascii art generation.')
        path = (self.process_dir / 'Frames' / f'frame{frame}.png') if self.is_video else self.path
        definition = self.definition[frame]
        chars = self.chars[frame]
        img = Image.open(path).resize((definition, self.definition_height)).convert('L')
        resp = ''
        for k, pixel in enumerate(img.getdata(), 1):
            char = chars[(pixel * (len(chars) - 1)) // 255]
            resp += char
            if not k % definition:
                resp += '\n'
        self.ascii_art = resp
        return resp

    def draw_ascii_art(self, frame: Optional[int] = None, gravity: str = 'Northwest') -> str:
        """Draw the ascii art on top of the canvas using ImageMagick.

        :param frame: The frame number, if working with videos/gifs.
        :param gravity: Used in ImageMagick to anchor the text.
        :return: The path of the generated image.
        """
        if self.is_video and frame is None:
            raise AsciifierException(
                'Frame was not specified for image generation.')
        canvas_path = str(self.process_dir / 'canvas.png')
        out_path = str(self.process_dir / 'NewFrames' / f'frame{frame}.png') \
            if frame else utils.safe_path(self.path)
        Magick.text_overlay(
            canvas_path, out_path, self.ascii_art, self.text_size, *self.txt[frame], gravity=gravity)
        return out_path

    def test_dynamic_params(self) -> List[Tuple[Any, ...]]:
        """Get the dynamic parameter values for every frame as a list of tuples."""
        resp = [list(range(1, self.frame_count + 1))]
        headers = ['Frame']
        for model, header in [(self.bg, 'BG Color'), (self.txt, 'Text Color'),
                              (self.definition, 'Definition'), (self.correction, 'Correction'), (self.chars, 'Chars')]:
            if model.is_dynamic:
                resp.append([model[i] for i in range(1, self.frame_count + 1)])
                headers.append(header)
        return [tuple(headers)] + list(zip(*resp))

    def remove_process_dir(self) -> None:
        """Remove the asciipixels process directory. This method is called when exiting context."""
        shutil.rmtree(self.process_dir)

    def video_to_frames(self) -> None:
        """Save every frame of ``self.path`` into the asciipixels dir."""
        FFmpeg.video_to_frames(self.str_path, str(self.process_dir / 'Frames' / 'frame%01d.png'))

    def frames_to_video(self, out_path: Optional[str] = None, ext: str = 'mp4') -> str:
        """Convert every frame of the NewFrames dir into a video.

        :param out_path: The output path.
        :param ext: The output extension. Defaults to mp4.
        :return: The output path.
        """
        if out_path is None:
            out_path = utils.safe_path(self.path, ext=ext)
        FFmpeg.frames_to_video(
            str(self.process_dir / 'NewFrames' / 'frame%01d.png'), out_path, self.fps, ext == 'gif')
        return out_path

    def finalize_video(self, ext: str = 'mp4') -> str:
        """Run ``frames_to_video``. Extract the audio of the original video and join it with the new one."""
        video_path = str(self.process_dir / f'video.{ext}')
        audio_path = str(self.process_dir / 'audio.aac')
        out_path = utils.safe_path(self.path)
        self.frames_to_video(video_path)
        try:
            FFmpeg.extract_audio(self.str_path, audio_path)
            has_audio = True
        except FFmpegException:
            has_audio = False
        w, h = self.out_dimensions
        FFmpeg.join_streams(video_path, out_path, w, h, (audio_path if has_audio else None))
        return out_path


class Magick:
    """Class with static functions wrapping important ImageMagick commands."""

    @staticmethod
    def dimensions(path: str) -> Tuple[int, int]:
        code, stdout = utils.run(identify, '-format', r'%wx%h', path)
        if code:
            raise MagickException('File does not exist or format not supported.')
        # noinspection PyTypeChecker
        return tuple(map(int, stdout.split('x')))

    @staticmethod
    def blank_png(path: str, width: int, height: int, r: int, g: int, b: int):
        code, stdout = utils.run(convert, '-size', f'{width}x{height}', f'xc:rgba({r},{g},{b},1)', path)
        if code:
            raise MagickException('File format not supported.')

    @staticmethod
    def text_overlay(
            path: str, out_path: str, text: str, size: int, r: int, g: int, b: int, gravity: str = 'Northwest'):
        code, stdout = utils.run(
            convert, str(path), '-gravity', gravity, '-font', 'Courier', '-pointsize', str(size), '-fill',
            f'rgba({r},{g},{b},1)', '-interline-spacing', '0', '-annotate', '+0+0', text, out_path)
        if code:
            raise MagickException('File does not exist or format not supported.')

    @staticmethod
    def text_dimensions(cols: int, lines: int, size: int, w: int, h: int) -> Tuple[int, int]:
        text = '\n'.join(['#' + '|' * (cols - 2) + '#'] * lines)
        code, stdout = utils.run(
            convert, '-size', f'{w}x{h}', 'xc:white', '-gravity', 'Northwest', '-font', 'Courier', '-pointsize',
            str(size), '-fill', 'black', '-undercolor', 'none', '-annotate', '+0+0', text, '-trim', 'info:')
        if code:
            raise MagickException('File does not exist or format not supported.')
        # noinspection PyTypeChecker
        return tuple(map(int, stdout.split(' ')[2].split('x')))


class FFmpeg:
    """Class with static functions wrapping important FFmpeg commands."""

    @staticmethod
    def dimensions(path: str) -> Tuple[int, int]:
        code, stdout = utils.run(
            ffprobe, path, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
            'stream=width,height', '-of', 'csv=s=x:p=0')
        if code:
            raise FFmpegException('File does not exist or format not supported.')
        dimensions = tuple(map(int, stdout.split('x')))
        code, stdout = utils.run(
            ffprobe, '-i', str(path), '-loglevel', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream_tags=rotate', '-of', 'default=nw=1:nk=1')
        if stdout == '90':
            return dimensions[1], dimensions[0]
        # noinspection PyTypeChecker
        return dimensions

    @staticmethod
    def fps(path: str) -> int:
        code, stdout = utils.run(
            ffprobe, path, '-v', '0', '-select_streams', 'v', '-print_format', 'flat',
            '-show_entries', 'stream=r_frame_rate')
        if code:
            raise FFmpegException('File does not exist or format not supported.')
        stdout = stdout.split('frame_rate="')[-1].split('"')[0].split('/')
        if len(stdout) > 1:
            return round(int(stdout[0]) / int(stdout[1]))
        return int(stdout[0])

    @staticmethod
    def frame_count(path: str) -> int:
        code, stdout = utils.run(
            ffprobe, path, '-select_streams', 'v:0', '-count_packets', '-show_entries',
            'stream=nb_read_packets', '-of', 'csv=p=0')
        if code:
            raise FFmpegException('File does not exist or format not supported.')
        try:
            return int(stdout)
        except ValueError:
            return int(stdout[:-1])

    @staticmethod
    def video_to_frames(path: str, out_path_pattern: str) -> None:
        code, stdout = utils.run(ffmpeg, '-i', path, out_path_pattern)
        if code:
            raise FFmpegException('File does not exist or format(s) not supported.')

    @staticmethod
    def frames_to_video(path_pattern: str, out_path: str, fps: int, gif: bool = False) -> None:
        if gif:
            code, stdout = utils.run(ffmpeg, '-f', 'image2', '-framerate', str(fps), '-i', path_pattern, out_path)
        else:
            code, stdout = utils.run(
               ffmpeg, '-r', str(fps), '-i', path_pattern, '-framerate', str(fps), '-c:v', 'libx264',
               '-pix_fmt', 'yuv420p', out_path)
        if code:
            raise FFmpegException('File does not exist or format(s) not supported.')

    @staticmethod
    def extract_audio(path: str, out_path: str) -> None:
        code, stdout = utils.run(ffmpeg, '-i', path, '-vn', '-acodec', 'copy', out_path)
        if code:
            raise FFmpegException('File does not have an audio stream.')

    @staticmethod
    def join_streams(path: str, out_path: str, w: int, h: int, audio_path: Optional[str] = None) -> None:
        if audio_path is None:
            code, stdout = utils.run(ffmpeg, '-i', path, '-vf', f'scale={w}:{h}', '-crf', '18', out_path)
        else:
            code, stdout = utils.run(
                ffmpeg, '-i', path, '-i', audio_path, '-vf', f'scale={w}:{h}', '-map', '0:v', '-map', '1:a',
                '-crf', '18', '-shortest', out_path)
        if code:
            raise FFmpegException('File does not exist or format(s) not supported.')
