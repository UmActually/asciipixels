from typing import Union, Callable
from os import PathLike
from pathlib import Path

SomeSortOfPath = Union[str, PathLike, Path]
Number = Union[int, float]
Color = Union[int, tuple[int, int, int]]
OptionalSize = Union[int, tuple[int, int], None]

DynamicInt = Union[Callable[[int], int], int]
DynamicFloat = Union[Callable[[int], float], float]
DynamicStr = Union[Callable[[int], str], str]
DynamicColor = Union[Callable[[int], Color], Color]


class AsciifierException(Exception):
    pass


class MagickException(Exception):
    pass


class FFmpegException(Exception):
    pass
