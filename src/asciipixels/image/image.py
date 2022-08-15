from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Optional, Tuple, List
from ..core import CoreAsciifier
from .. import utils
from ..typealiases import (
    SomeSortOfPath, Color, OptionalSize, DynamicInt, DynamicFloat, DynamicStr, DynamicColor)


__all__ = ['asciify', 'dynamic_asciify']


def dynamic_single_frame(frame: int, core: CoreAsciifier) -> None:
    """This function is submitted to the ProcessPoolExecutor."""
    core.figure_out_sizes(frame, fine_tune=False, even_sizes=True)
    core.generate_ascii_art(frame)
    core.draw_ascii_art(frame, gravity='Center')


def asciify(
        path: SomeSortOfPath, bg_color: Color = 30, txt_color: Color = 255, definition: int = 100,
        out_width: OptionalSize = None, strict_out_dimensions: bool = False, correction: Optional[float] = None,
        chars: str = ' .:-=+*$@#', reverse_chars: bool = False, save_txt: bool = False) -> str:

    """**Convert an image to ascii art and save it in the same directory.**

        >>> asciify('foo.png')
        [Saves the image and returns the ascii art string]

        >>> asciify('foo.png', out_width=1920, save_txt=True)
        [Saves the image, with a specified width of 1920, saves text in file and returns ascii art string.]

    :param path: The path to the image file.
    :param bg_color: The color of the background as tuple or integer (0-255). Defaults to dark gray (30).
    :param txt_color: The color of the ascii overlay as tuple or integer (0-255). Defaults to white (255).
    :param definition: The number of characters in the horizontal axis. Defaults to 100.
    :param out_width: The pixel width of the new image, or pass a tuple for width and height.
        In that case, width is prioritized when creating the image. Defaults to approximate input image dimensions.
    :param strict_out_dimensions: Set to True to use the exact specified output dimensions. Defaults to False.
    :param correction: The factor of compensation for the non-square nature of an ascii character. A value between
        zero and one shrinks the input image height. This is generally what we want. Defaults to approximate
        original proportions.
    :param chars: The string of characters to be used in the ascii art. Any length is accepted, but the characters
        should be in dimmest to brightest order. Defaults to ' .:-=+*$@#'
    :param reverse_chars: Whether to reverse the chars order, in case it's dark text on light background.
        Defaults to False.
    :param save_txt: Whether to save the ascii art in a text file. Will be saved in the same directory as the input
        image. Defaults to False.
    :return: The ascii art as a string.
    """

    core = CoreAsciifier(
        str(path), bg_color, txt_color, definition, out_width, strict_out_dimensions, correction, chars, reverse_chars)

    with core:
        core.figure_out_sizes()
        core.generate_canvas()
        resp = core.generate_ascii_art()
        core.draw_ascii_art()

        if save_txt:
            txt_path = utils.safe_path(path, ext='txt', as_path_obj=True)
            txt_path.write_text(core.ascii_art)

    return resp


def dynamic_asciify(
        path: SomeSortOfPath, bg_color: DynamicColor = 30, txt_color: DynamicColor = 255, definition: DynamicInt = 100,
        out_width: OptionalSize = None, strict_out_dimensions: bool = False, frame_count: int = 10, fps: int = 5,
        gif: bool = True, correction: Optional[DynamicFloat] = None, chars: DynamicStr = " .:-=+*$@#",
        reverse_chars: bool = False, quiet: bool = False,
        test_dynamic_params: bool = False) -> Optional[List[Tuple[Any, ...]]]:

    """**Convert an image to an ascii art gif or video where the parameters can change over time.**

    With this function, you are able to pass some parameters of the ascii art generation as either static (hard-coded)
    or dynamic (**callable**) parameters. When passed as callables, the only argument should be the frame number, and
    the return value should be the corresponding parameter value.

    This function **needs** a ``if __name__ == "__main__"`` check in the entry point of your code, unless you are using
    interactive python on the command line.

        >>> dynamic_asciify('foo.png', definition=lambda frame: frame * 5 + 80)
        [Saves a gif where every frame the ascii art definition increments by 5.]

        >>> def frame_specific_color(frame):
        ...     if frame <= 10:
        ...         return 80, 10, 10
        ...     return 10, 10, 80
        >>> dynamic_asciify('foo.png', bg_color=frame_specific_color, frame_count=20)
        [Saves a gif where the background is red in the first 10 frames, and blue in the rest.]

    :param path: The path to the image file.
    :param bg_color: Dynamic-compatible. The color of the background as tuple or integer (0-255). Defaults to dark
        gray (30).
    :param txt_color: Dynamic-compatible. The color of the ascii overlay as tuple or integer (0-255). Defaults to
        white (255).
    :param definition: Dynamic-compatible. The number of characters in the horizontal axis. Defaults to 100.
    :param out_width: The pixel width of the new image, or pass a tuple for width and height.
        In that case, width is prioritized when creating the image. Defaults to approximate input image dimensions.
    :param strict_out_dimensions: Set to True to use the exact specified output dimensions. Defaults to False.
    :param frame_count: The total amount of frames to generate. Defaults to 10.
    :param fps: The FPS of the result gif or video. Defaults to 5.
    :param gif: Whether to save as gif or mp4. Defaults to True.
    :param correction: Dynamic-compatible. The factor of compensation for the non-square nature of an ascii character.
        A value between zero and one shrinks the input image height. This is generally what we want. Defaults to
        approximate original proportions.
    :param chars: Dynamic-compatible. The string of characters to be used in the ascii art. Any length is accepted,
        but the characters should be in dimmest to brightest order. Defaults to ' .:-=+*$@#'
    :param reverse_chars: Whether to reverse the chars order, in case it's dark text on light background.
        Defaults to False.
    :param quiet: Set to True to avoid printing progress to the console. Defaults to False.
    :param test_dynamic_params: Set to True to avoid converting the image to ascii art, and only return the
        dynamic parameter values for every frame as a list of tuples. Defaults to False.
    :return: None, or the dynamic parameter values when test_dynamic_params is True.
    """

    utils.multiprocessing_guard()
    _print = utils.conditional_print(quiet)

    core = CoreAsciifier(
        str(path), bg_color, txt_color, definition, out_width, strict_out_dimensions,
        correction, chars, reverse_chars, frame_count, fps)

    with core:
        if test_dynamic_params:
            return core.test_dynamic_params()

        # dimensions = core.out_dimensions
        max_def_frame = core.definition.value.index(max(core.definition.value))
        core.figure_out_sizes(max_def_frame, even_sizes=True)
        core.generate_canvas(max_def_frame)
        # core.out_dimensions = dimensions

        _print('Generating ASCII Art...', end='')
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(dynamic_single_frame, f, core) for f in range(1, frame_count + 1)]
            for k, future in enumerate(as_completed(futures), 1):
                future.result()
                progress = f'Generating ASCII Art... {int(100 * (k / frame_count))}%.'
                _print('\r', end='')
                _print(progress, end='')
        _print()

        core.frames_to_video(ext=('gif' if gif else 'mp4'))
