from typing import Any
from enums import MessageType
from json import dumps

from ..enums.cmd import CommandType

from ..const import MCAM, MDRW

class BaseMessage(object):
    _raw: str
    type: MessageType
    _type: bytes
    size: int
    _magic1: Any
    _magic2: Any

    @classmethod
    def from_buffer(cls, buff):
        return cls(
            _raw=buff,
            _type=buff[1],
            type=MessageType(buff[1]),
            size=int.from_bytes(buff[2:4], byteorder='big'),
            _magic1=buff[0],
            _magic2=buff[4],
        )
    
    def __str__(self) -> str: return f"{self.__class__.__name__}(type={self.type.name},size={self.size})"

    def to_json(self) -> str: return dumps(self, indent=4)

class DRWMessage(BaseMessage):
    channel: Any
    index: Any
    data: dict[str, Any]

    @classmethod
    def from_buffer(cls, buff):
        return cls(
            _raw=buff,
            _type=buff[1],
            type=MessageType(buff[1]),
            size=int.from_bytes(buff[2:4], byteorder='big'),
            _magic1=buff[0],
            _magic2=buff[4],
            channel=buff[5],
            index=int.from_bytes(buff[6:8], byteorder='big'),
            data=buff[8:],
        )
    
    def to_buffer(self, index_ref: list[int]):
        buf = bytearray(len(self.data) + 8)
        buf[0] = MCAM
        buf[1] = MessageType.DRW
        buf[2:4] = (len(self.data) + 4).to_bytes(2, 'big')
        buf[4] = MDRW
        buf[5] = self.channel
        buf[6:8] = (index_ref[0] & 0xFFFF).to_bytes(2, 'big')
        index_ref[0] += 1
        buf[8:] = self.data
        return buf

    def __str__(self) -> str: return f"{self.__class__.__name__}(type={self.type.name},size={self.size},channel={self.channel},index={self.index},data={self.data})"

class CommandData(object):
    pro: str # commandtype as string
    cmd: CommandType

    def to_json(self):
        return dumps(self)

class CommandMessage(DRWMessage):
    user: str = "admin"
    pwd: str = "6666"
    devmac: str = "0000"
    data: {
        'pro': None,
        'cmd': None
    }

    def __init__(self, data: CommandData = None) -> None:
        if data: self.data = data.to_json()

    def to_buffer(self, data: Any|bytes):
        if not isinstance(data, bytes): data = data.encode('ascii')
        buf = bytearray(len(data) + 8)
        buf[0] = 0x06
        buf[1] = 0x0a
        buf[2] = 0xa0
        buf[3] = 0x80
        buf[4:8] = len(data).to_bytes(4, 'little')
        buf[8:] = data
        return data

    def __str__(self) -> str: return f"{self.__class__.__name__}(type={self.type.name},size={self.size},channel={self.channel},index={self.index},data={self.data})"