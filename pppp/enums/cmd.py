from enum import Enum

class CommandType(Enum):
    SET_CYPUSH = 1
    CHECK_USER = 100
    GET_PARMS = 101
    DEV_CONTROL = 102
    EDIT_USER = 106
    GET_ALARM = 107
    SET_ALARM = 108
    STREAM = 111
    GET_WIFI = 112
    SCAN_WIFI = 113
    SET_WIFI = 114
    SET_DATETIME = 126
    PTZ_CONTROL = 128
    GET_RECORD_PARAM = 199
    TALK_SEND = 300
    SET_WHITELIGHT = 304
    GET_WHITELIGHT = 305
    GET_CLOUD_SUPPORT = 9000

    @staticmethod
    def str(input):
        return "CMD_" + CommandType(input).name

class CommandResult(Enum):
    WrongPassword = -3
    WrongUsername = -1
    Failed = 0
    Success = 1