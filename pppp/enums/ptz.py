from enum import Enum

class PTZ(Enum):
    TILT_UP_START = 0
    TILT_UP_STOP = 1
    TILT_DOWN_START = 2
    TILT_DOWN_STOP = 3
    PAN_LEFT_START = 4
    PAN_LEFT_STOP = 5
    PAN_RIGHT_START = 6
    PAN_RIGHT_STOP = 7