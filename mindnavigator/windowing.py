from enum import Flag, auto


class ResizeEdge(Flag):
    NONE = 0
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOTTOM = auto()
