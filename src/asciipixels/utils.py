from typing import Any, Union, Optional, Tuple, Callable, NoReturn
import subprocess
import os
import sys
import warnings
from pathlib import Path
from .typealiases import SomeSortOfPath


def run(executable: str, *args: str, get_stderr=False) -> Tuple[int, str]:
    """Run a system command."""
    if get_stderr:
        process = subprocess.run([executable, *args], text=True, capture_output=True)
        return process.returncode, process.stderr.strip('\n')
    process = subprocess.run([executable, *args], text=True, capture_output=True)
    return process.returncode, process.stdout.strip('\n')


def multiprocessing_guard() -> Optional[NoReturn]:
    """Ensure that the top-level script has a 'if __name__ == "__main__"' check."""
    if int(os.environ.get('ASCIIPIXELS_PROCESS', '0')):
        warnings.warn(
            '\nAn asciipixels function is being repeatedly called when helper processes are spawned.\n'
            'This can be solved by adding a \'if __name__ == "__main__"\' check in the entry point of your code.\n'
            'Example:\n\nimport asciipixels as ap\n\nif __name__ == "__main__":\n    ap.video.asciify("foo.mp4")\n\n'
            'Check the README for more details.',
            RuntimeWarning)
        sys.exit()
    os.environ['ASCIIPIXELS_PROCESS'] = '1'

    # if inspect.stack(0)[-1].filename == '<string>':
    #     sys.tracebacklimit = 0
    #     raise MultiprocessingException(
    #         'An asciipixels function is being called again when child processes are spawned. This can be solved '
    #         'by adding a \'if __name__ == "__main__"\' check in the entry point of your code.')


def conditional_print(quiet: bool) -> Callable:
    """Return a conditional print function."""
    def _print(*values: Any, end: str = '\n'):
        if not quiet:
            print(*values, end=end)
    return _print


def safe_path(path: SomeSortOfPath, ext: str = None, as_path_obj: bool = False) -> Union[str, Path]:
    """Return whatever path is available by incrementing a suffix number in the filename. If the
    passed input path doesn't exist, return it."""
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists():
        return path
    if ext is None:
        ext = path.suffix[1:]

    index = -1
    parent = path.parent
    stem = path.stem
    while stem[index].isdigit():
        index -= 1

    try:
        k = int(stem[index + 1:]) + 1
        stem = stem[:index + 1]
    except ValueError:
        k = 2

    while (parent / f'{stem}{k}.{ext}').exists():
        k += 1

    resp = parent / f'{stem}{k}.{ext}'
    return resp if as_path_obj else str(resp)
