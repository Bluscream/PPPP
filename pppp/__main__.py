import socket
import threading
from eventemitter import EventEmitter
import encryption  # Assuming 'crypt' is a module you have for encryption
import adpcm # Assuming 'adpcm' is a module you have for ADPCM handling
from .const import *
from .enums import *
from .types import *
from logging import getLogger, Logger
from argparse import Namespace

class PPPP(EventEmitter):
    logger: Logger
    socket: socket.socket
    IP_DEBUG_MSG: str
    DRW_PACKET_INDEX: int
    lastVideoFrame: int
    videoBoundaries: set
    videoReceived: list
    videoOverflow: bool
    lastAudioFrame: int
    isConnected: bool
    punchCount: int
    reconnectDelay: int
    broadcastDestination: str
    myIpAddressToBind: str

    def __init__(self, options: Namespace):
        super().__init__()
        self.logger = getLogger(__class__.__name__)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.IP_DEBUG_MSG = None
        self.DRW_PACKET_INDEX = 0
        self.lastVideoFrame = -1
        self.videoBoundaries = set()
        self.videoReceived = []
        self.videoOverflow = False
        self.lastAudioFrame = -1
        self.isConnected = False
        self.punchCount = 0
        self.reconnectDelay = 500
        self.broadcastDestination = options['broadcastip']
        self.myIpAddressToBind = options['thisip']

        self.socket.bind((self.myIpAddressToBind, 0))  # Bind to the given IP and a random port

        # Event handlers
        self.socket.on('error', self.on_error)
        self.socket.on('listening', self.on_listening)
        self.socket.on('message', self.on_message)

    def on_error(self, err):
        print(f'closing socket! error:\n{err}')
        self.socket.close()
        self.emit('error', err)

    def on_listening(self):
        address = self.socket.getsockname()
        print(f'socket listening {address[0]}:{address[1]}')
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.send_broadcast()

#region recieve

    def on_message(self, msg, rinfo):
        d = encryption.decrypt(msg)

        if self.IP_DEBUG_MSG:
            self.socket.sendto(d, (self.IP_DEBUG_MSG, 3300))

        p: BaseMessage
        try:
            p = BaseMessage.from_buffer(d)
        except Exception as e:
            print(f"Error while parsing packet: {str(e)}")
            return
        try:
            self.handle_packet(p, msg, rinfo)
        except Exception as e:
            print(f"Error while handling packet: {str(e)}")

    def handle_packet(self, msg: BaseMessage|DRWMessage, raw, rinfo):
        self.emit('debug', f"Received {msg}")

        match(msg.type):
            case(MessageType.PUNCH): # Reply to MSG_PUNCH to establish connection
                print('MSG_PUNCH received')
                if self.punchCount < 5:
                    self.punchCount += 1
                    self.socket.sendto(raw, (rinfo[0], rinfo[1]))
                    self.emit('log', f"Sent {MessageType.PUNCH.name}")

            case(MessageType.P2P_RDY):
                print('MSG_P2P_RDY received')
                self.CAM_IP = rinfo[0]
                self.CAM_PORT = rinfo[1]

                if not self.is_connected:
                    self.is_connected = True
                    self.reconnect_delay = 500
                    # Use threading.Timer to mimic JavaScript's setTimeout
                    threading.Timer(0.5, lambda: self.emit('connected', rinfo[0], rinfo[1])).start()

            
            case(MessageType.ALIVE): # Reply to MSG_ALIVE
                print('MSG_ALIVE received')
                self.send_simple(MessageType.ALIVE_ACK)
                self.emit('log', f"Acknowledged {MessageType.ALIVE}")

            
            case(MessageType.CLOSE): # Reply to MSG_CLOSE
                print('MSG_CLOSE received')
                if self.is_connected:
                    self.is_connected = False
                    self.emit('disconnected', self.CAM_IP, self.CAM_PORT)
                self.send_simple(MessageType.ALIVE_ACK, 12)

            case(MessageType.DRW): # Handle MSG_DRW
                buf = bytearray(10)
                buf[0] = MCAM
                buf[1] = MessageType.DRW_ACK
                buf[2:4] = (6).to_bytes(2, 'big')
                buf[4] = 0xd1
                buf[5] = msg.channel
                buf[6:8] = (1).to_bytes(2, 'big')
                buf[8:10] = msg.index.to_bytes(2, 'big')
                self.send_enc(buf)

                match(msg.channel):
                    case(Channel.Command): # Handle CMD Response
                        print('CMD Response received')
                        if msg['data'].startswith(b'\x06\x0a'):
                            data = msg['data'][8:]
                            _msg = data.decode('ascii')
                            self.emit('cmd', _msg)

                    case(Channel.Video): # Handle Video
                        if msg['index'] > 65400: # Handle MSG_DRW packet index overflow
                            self.video_overflow = True

                        if self.video_overflow and msg['index'] < 65400:
                            self.last_video_frame = -1
                            self.video_overflow = False
                            self.video_boundaries.clear()
                            self.video_received = []

                        if msg['data'].startswith(b'\x55\xaa\x15\xa8\x03\x00'):
                            self.video_received[msg['index']] = msg['data'][0x20:]
                            self.video_boundaries.add(msg['index'])
                        else:
                            self.video_received[msg['index']] = msg['data']
                        self.get_video_frame()

                    case(Channel.Audio): # Handle Audio
                        if self.last_audio_frame < msg['index']:
                            raw = msg['data'][0x20:] if msg['data'].startswith(b'\x55\xaa\x15\xa8\xaa\x01') else msg['data']
                            decoded = adpcm.decode(raw)
                            self.last_audio_frame = msg['index']
                            self.emit('audio_frame', {'frame': decoded, 'packet_index': msg['index']})

                    case(_):
                        self.logger.error(f"Unknown channel: {msg.channel}")
#endregion recieve     

#region send

    def send_broadcast(self):
        self.socket.sendto(BroadCastBytes, (self.broadcastDestination, 32108))
        print(f'broadcast Message sent to {self.broadcastDestination}')

        if not self.isConnected and self.punchCount == 0:
            threading.Timer(self.reconnectDelay / 1000, self.send_broadcast).start()
            self.reconnectDelay += 1

    def send_simple(self, type: MessageType, amount: int = 1):
        buf = bytearray(4)
        buf[0] = MCAM
        buf[1] = type
        buf[2:4] = (amount).to_bytes(2, 'big')
        self.send_enc(buf)
        self.emit('debug', f"Sent {type} x{amount}")

    def send_enc(self, msg):
        if isinstance(msg, bytes):
            message = msg
        else:
            message = bytes.fromhex(msg)
        self.send(encryption.encrypt(message))

    def send(self, msg):
        if isinstance(msg, bytes):
            message = msg
        else:
            message = bytes.fromhex(msg)
        self.socket.sendto(message, (self.CAM_IP, self.CAM_PORT))

        if self.IP_DEBUG_MSG:
            self.socket.sendto(encryption.decrypt(message), (self.IP_DEBUG_MSG, 3301))

    def send_cmd_packet(self, msg): # replace with CommandMessage.to_buffer()
        if isinstance(msg, bytes):
            data = msg
        else:
            data = msg.encode('ascii')
        buf = bytearray(len(data) + 8)
        buf[0] = 0x06
        buf[1] = 0x0a
        buf[2] = 0xa0
        buf[3] = 0x80
        buf[4:8] = len(data).to_bytes(4, 'little')
        buf[8:] = data
        self.send_drw_packet(0, buf)
        print(f"CMD sent: {data.decode('ascii')}")

    def send_drw_packet(self, channel, data): # replace with DRWMessage.to_buffer()
        buf = bytearray(len(data) + 8)
        buf[0] = MCAM
        buf[1] = MessageType.DRW
        buf[2:4] = (len(data) + 4).to_bytes(2, 'big')
        buf[4] = MDRW
        buf[5] = channel
        buf[6:8] = (self.DRW_PACKET_INDEX & 0xFFFF).to_bytes(2, 'big')
        self.DRW_PACKET_INDEX += 1
        buf[8:] = data
        self.send_enc(buf)
        print(f'DRW packet sent (len: {len(buf)})')

    def sendCommand(self, command, args):
        fixed_data = {
            'user': 'admin',
            'pwd': '6666',
        }
        data = {
            'pro': CMD_DICT[command],
            'cmd': command
        }
        strData = json.dumps({**data, **args, **fixed_data})
        self.sendCMDPacket(strData)

    def sendCMDCheckUser(self):
        self.sendCommand(CommandType.CHECK_USER)

    def sendCMDrequestVideo1(self):
        self.logger.info('requesting 640x480 video stream')
        self.sendCommand(CommandType.STREAM, {'video': 1})

    def sendCMDrequestVideo2(self):
        self.logger.info('requesting 320x240 video stream')
        self.sendCommand(CommandType.STREAM, {'video': 2})

    def sendCMDrequestAudio(self):
        self.logger.info('requesting ADPCM audio stream')
        self.sendCommand(CommandType.STREAM, {'audio': 1})

    def sendCMDsetWifi(self, ssid, pw):
        self.sendCommand(CommandType.SET_WIFI, {
            'wifissid': ssid,
            'encwifissid': ssid,
            'wifipwd': pw,
            'encwifipwd': pw,
            'encryption': 1
        })

    def sendCMDscanWifi(self):
        self.sendCommand(CommandType.SCAN_WIFI)

    def sendCMDgetWifi(self):
        self.sendCommand(CommandType.GET_WIFI)

    def sendCMDgetRecordParam(self):
        self.sendCommand(CommandType.GET_RECORD_PARAM)

    def sendCMDgetParams(self):
        self.sendCommand(CommandType.GET_PARMS)

    def sendCMDIr(self, isOn):
        self.sendCommand(CommandType.DEV_CONTROL, {'icut': 1 if isOn else 0})

    def sendCMDLamp(self, isOn):
        self.sendCommand(CommandType.DEV_CONTROL, {'lamp': 1 if isOn else 0})

    def sendCMDTalkSend(self):
        self.sendCommand(CommandType.TALK_SEND, {'isSend': 1})

    def sendCMDGetWhiteLight(self):
        self.sendCommand(CommandType.GET_WHITELIGHT)

    def sendCMDSetWhiteLight(self, isOn):
        self.sendCommand(CommandType.SET_WHITELIGHT, {'status': 1 if isOn else 0})

    def sendCMDHeartBeat(self):
        self.sendCommand(CommandType.DEV_CONTROL, {'heart': 1})

    def sendCMDsetDateTime(self, my_timezone_offset, timestamp):
        self.sendCommand(CommandType.SET_DATETIME, {
            'tz': my_timezone_offset,
            'time': timestamp,
        })

    def sendCMDsetPushServer(self):
        self.sendCommand(CommandType.SET_CYPUSH, {
            'pushIp': '192.168.7.20',
            'pushPort': 5432,
        })
        unused_args = {
            'pushInterval': 30,
            'isPushVideo': 0,
            'isPushPic': 0,
            'cyAdmin': '<username>',
            'cyPwd': '<password>',
        }

    def sendCMDsetAlarm(self):
        self.sendCommand(CommandType.SET_ALARM, {
            'pirPush': 1,
            'pirenable': 1,
            'pirsensitive': 2,
            'pirDelayTime': 5,
            'pirvideo': 0,
            'pirvideotime': 0,
        })

    def sendCMDeditUser(self, userToEdit, newPwd, newUsername):
        self.sendCommand(CommandType.EDIT_USER, {
            'edituser': userToEdit,
            'newpwd': newPwd,
            'newuser': newUsername,
        })

    def sendCMDGetDeviceFirmwareInfo(self):
        self.sendCommand(CommandType.GET_CLOUD_SUPPORT)

    def sendCMDGetAlarm(self):
        self.sendCommand(CommandType.GET_ALARM)

    def sendCMDPtzControl(self, direction):
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 0, 'value': direction})

    def sendCMDPtzStop(self):
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 0, 'value': PTZ.PAN_LEFT_STOP})
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 0, 'value': PTZ.PAN_RIGHT_STOP})
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 0, 'value': PTZ.TILT_DOWN_STOP})
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 0, 'value': PTZ.TILT_UP_STOP})

    def sendCMDPtzReset(self):
        self.sendCommand(CommandType.PTZ_CONTROL, {'parms': 1, 'value': 132})

    def sendCMDReboot(self):
        self.sendCommand(CommandType.DEV_CONTROL, {'reboot': 1})

    def sendCMDReset(self):
        self.sendCommand(CommandType.DEV_CONTROL, {'reset': 1})

#endregion send

    def get_video_frame(self):
        if len(self.videoBoundaries) <= 1:
            return None
        sorted_boundaries = sorted(self.videoBoundaries)
        index = sorted_boundaries[-2]
        last_index = sorted_boundaries[-1]

        if index == self.lastVideoFrame:
            return None

        complete = True
        out = bytearray()
        completeness = ''
        for i in range(index, last_index):
            if self.videoReceived[i] is not None:
                out.extend(self.videoReceived[i])
                completeness += 'x'
            else:
                complete = False
                completeness += '_'

        if complete:
            self.lastVideoFrame = index
            self.emit('videoFrame', {'frame': bytes(out), 'packetIndex': index})
            # Free memory where videoReceived[<index]
            for i in range(index):
                self.videoReceived[i] = None

    def destroy(self):
        if self.isConnected:
            buf = bytes([MCAM, MessageType.CLOSE, 0, 0])
            for _ in range(3): self.sendEnc(buf)
        self.socket.close()