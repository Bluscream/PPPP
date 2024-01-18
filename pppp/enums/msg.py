from enum import Enum

class MessageType(Enum):
    PUNCH = 0x41
    P2P_RDY = 0x42
    DRW = 0xd0
    DRW_ACK = 0xd1
    ALIVE = 0xe0
    ALIVE_ACK = 0xe1
    CLOSE = 0xf0

    @staticmethod
    def str(input):
        return "MSG_" + MessageType(input).name