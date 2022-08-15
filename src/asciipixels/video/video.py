from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Union, Optional, Tuple, List
from time import perf_counter
from ..core import CoreAsciifier
from .. import utils
from ..typealiases import (
    SomeSortOfPath, Number, Color, OptionalSize, DynamicInt, DynamicFloat, DynamicStr, DynamicColor)


__all__ = ['asciify', 'dynamic_asciify']


def ld_0(num: Union[Number, str]) -> str:
    """Leading zero version of a number."""
    return '0' * (int(num) < 10) + str(num)


def in_minutes(seconds: Number) -> str:
    """Display a seconds value as MM:SS"""
    minutes = seconds // 60
    return ld_0(minutes) + ':' + ld_0(seconds - minutes * 60)


def time_remaining(
        progress: Number, whole: Number, start_time: float, curr_time: float, last_checked: float) -> Optional[str]:
    """ALGORITHM IS NOT FINAL. Estimates remaining time out of a progress/whole operation."""
    if (curr_time - last_checked) > 2:
        return in_minutes(int((curr_time - start_time) * (whole - progress) / progress))


def asciify_single_frame(frame: int, core: CoreAsciifier) -> None:
    """This function is submitted to the ProcessPoolExecutor."""
    core.generate_ascii_art(frame)
    core.draw_ascii_art(frame)


def dynamic_single_frame(frame: int, core: CoreAsciifier) -> None:
    """This function is submitted to the ProcessPoolExecutor."""
    core.figure_out_sizes(frame, fine_tune=False, even_sizes=True)
    core.generate_ascii_art(frame)
    core.draw_ascii_art(frame, gravity='Center')


def asciify(
        path: SomeSortOfPath, bg_color: Color = 30, txt_color: Color = 255, definition: int = 100,
        out_width: OptionalSize = None, strict_out_dimensions: bool = False, correction: Optional[float] = None,
        chars: str = " .:-=+*$@#", reverse_chars: bool = False, quiet: bool = False) -> None:

    """**Convert video to ascii art and save it in the same directory.**

    This function **needs** a ``if __name__ == "__main__"`` check in the entry point of your code, unless you are using
    interactive python on the command line.

        >>> asciify('foo.mp4')
        [Saves the video]

        >>> asciify('foo.mp4', definition=80, out_width=1920)
        [Saves the video, with a specified definition of 80, and an output resolution of 1080p.]

    :param path: The path to the video file.
    :param bg_color: The color of the background as tuple or integer (0-255). Defaults to dark gray (30).
    :param txt_color: The color of the ascii overlay as tuple or integer (0-255). Defaults to white (255).
    :param definition: The number of characters in the horizontal axis. Defaults to 100.
    :param out_width: The pixel width of the new video, or pass a tuple for width and height.
        In that case, width is prioritized when creating the frames. Defaults to approximate input video dimensions.
    :param strict_out_dimensions: Set to True to use the exact specified output dimensions. Defaults to False.
    :param correction: The factor of compensation for the non-square nature of an ascii character. A value between
        zero and one shrinks the input frame height. This is generally what we want. Defaults to approximate
        original proportions.
    :param chars: The string of characters to be used in the ascii art. Any length is accepted, but the characters
        should be in dimmest to brightest order. Defaults to ' .:-=+*$@#'
    :param reverse_chars: Whether to reverse the chars order, in case it's dark text on light background.
        Defaults to False.
    :param quiet: Set to True to avoid printing progress to the console. Defaults to False.
    :return: None.
    """

    utils.multiprocessing_guard()
    _print = utils.conditional_print(quiet)

    path = str(path)
    core = CoreAsciifier(
        path, bg_color, txt_color, definition, out_width, strict_out_dimensions, correction, chars, reverse_chars)

    with core:
        _print('Converting video to frames...')
        core.video_to_frames()

        _print('Generating canvas...')
        core.figure_out_sizes(even_sizes=True)
        core.generate_canvas()

        _print('Generating ASCII Art...', end='')
        frame_count = core.frame_count
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(asciify_single_frame, f, core) for f in range(1, frame_count + 1)]
            start_time = perf_counter()
            last_checked = 0
            time_left = None
            for k, future in enumerate(as_completed(futures), 1):
                future.result()
                if quiet:
                    continue
                curr_time = perf_counter()
                calculated = time_remaining(k, frame_count, start_time, curr_time, last_checked)
                time_left = calculated or time_left
                progress = f'Generating ASCII Art... {int(100 * (k / frame_count))}%. {time_left} Remaining.'
                if calculated is not None:
                    last_checked = curr_time
                print('\r', end='')
                print(progress, end='')
        _print(f'\nCompleted in: {in_minutes(int(perf_counter() - start_time))}.')

        _print('Getting video ready...')
        core.finalize_video()


def dynamic_asciify(
        path: SomeSortOfPath, bg_color: DynamicColor = 30, txt_color: DynamicColor = 255,
        definition: DynamicInt = 100, out_width: OptionalSize = None, strict_out_dimensions: bool = False,
        correction: Optional[DynamicFloat] = None, chars: DynamicStr = " .:-=+*$@#", reverse_chars: bool = False,
        quiet: bool = False, test_dynamic_params: bool = False) -> Optional[List[Tuple[Any, ...]]]:

    """**Convert video to ascii art where the parameters can change over time.**

    With this function, you are able to pass some parameters of the ascii art generation as either static (hard-coded)
    or dynamic (callable) parameters. When passed as callables, the only argument should be the frame number, and the
    return value should be the corresponding parameter value.

    This function **needs** a ``if __name__ == "__main__"`` check in the entry point of your code, unless you are using
    interactive python on the command line.

        >>> dynamic_asciify('foo.mp4', definition=lambda frame: frame * 5 + 80)
        [Saves a video where every frame the ascii art definition increments by 5.]

        >>> def frame_specific_color(frame):
        ...     if frame <= 10:
        ...         return 80, 10, 10
        ...     return 10, 10, 80
        >>> dynamic_asciify('foo.mp4', bg_color=frame_specific_color)
        [Saves a video where the background is red in the first 10 frames, and blue in the rest.]

    :param path: The path to the video file.
    :param bg_color: Dynamic-compatible. The color of the background as tuple or integer (0-255). Defaults to dark
        gray (30).
    :param txt_color: Dynamic-compatible. The color of the ascii overlay as tuple or integer (0-255). Defaults to
        white (255).
    :param definition: Dynamic-compatible. The number of characters in the horizontal axis. Defaults to 100.
    :param out_width: The pixel width of the new video, or pass a tuple for width and height.
        In that case, width is prioritized when creating the frames. Defaults to approximate input video dimensions.
    :param strict_out_dimensions: Set to True to use the exact specified output dimensions. Defaults to False.
    :param correction: Dynamic-compatible. The factor of compensation for the non-square nature of an ascii character.
        A value between zero and one shrinks the input frame height. This is generally what we want. Defaults to
        approximate original proportions.
    :param chars: Dynamic-compatible. The string of characters to be used in the ascii art. Any length is accepted,
        but the characters should be in dimmest to brightest order. Defaults to ' .:-=+*$@#'
    :param reverse_chars: Whether to reverse the chars order, in case it's dark text on light background.
        Defaults to False.
    :param quiet: Set to True to avoid printing progress to the console. Defaults to False.
    :param test_dynamic_params: Set to True to avoid converting the video to ascii art, and only return the
        dynamic parameter values for every frame as a list of tuples. Defaults to False.
    :return: None, or the dynamic parameter values when test_dynamic_params is True.
    """

    utils.multiprocessing_guard()
    _print = utils.conditional_print(quiet)

    path = str(path)
    core = CoreAsciifier(
        path, bg_color, txt_color, definition, out_width, strict_out_dimensions, correction, chars, reverse_chars)

    with core:
        if test_dynamic_params:
            return core.test_dynamic_params()

        _print('Converting video to frames...')
        core.video_to_frames()

        _print('Generating canvas...')
        dimensions = core.out_dimensions
        core.figure_out_sizes(1, even_sizes=True)
        core.generate_canvas(1)
        core.out_dimensions = dimensions

        _print('Generating ASCII Art...', end='')
        frame_count = core.frame_count
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(dynamic_single_frame, f, core) for f in range(1, frame_count + 1)]
            start_time = perf_counter()
            for k, future in enumerate(as_completed(futures), 1):
                future.result()
                if quiet:
                    continue
                progress = f'Generating ASCII Art... {int(100 * (k / frame_count))}%.'
                print('\r', end='')
                print(progress, end='')
        _print(f'\nCompleted in: {in_minutes(int(perf_counter() - start_time))}.')

        _print('Getting video ready...')
        core.finalize_video()
