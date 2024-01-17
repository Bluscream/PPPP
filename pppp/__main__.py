import socket
import threading
from stream import EventEmitter
import crypt_1  # Assuming 'crypt' is a module you have for encryption
import adpcm  # Assuming 'adpcm' is a module you have for ADPCM handling

# Constants
MCAM = 0xf1
MDRW = 0xd1

MSG_PUNCH = 0x41
MSG_P2P_RDY = 0x42
MSG_DRW = 0xd0
MSG_DRW_ACK = 0xd1
MSG_ALIVE = 0xe0
MSG_ALIVE_ACK = 0xe1
MSG_CLOSE = 0xf0

TYPE_DICT = {
    MSG_PUNCH: 'MSG_PUNCH',
    MSG_P2P_RDY: 'MSG_P2P_RDY',
    MSG_DRW: 'MSG_DRW',
    MSG_DRW_ACK: 'MSG_DRW_ACK',
    MSG_ALIVE: 'MSG_ALIVE',
    MSG_ALIVE_ACK: 'MSG_ALIVE_ACK',
    MSG_CLOSE: 'MSG_CLOSE',
}

# Commands
CMD_SET_CYPUSH = 1
CMD_CHECK_USER = 100
# ... (other CMD constants)

CMD_DICT = {
    CMD_SET_CYPUSH: 'set_cypush',
    CMD_CHECK_USER: 'check_user',
    # ... (other CMD mappings)
}

# PTZ (Pan-Tilt-Zoom) Control Constants
PTZ_TILT_UP_START = 0
PTZ_TILT_UP_STOP = 1
# ... (other PTZ constants)

class PPPP(EventEmitter):
    def __init__(self, options):
        super().__init__()
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

    def on_message(self, msg, rinfo):
        pass # ... (message handling logic)


        # ... (continuing from the previous Python code)

    def send_broadcast(self):
        message = bytes.fromhex('2cba5f5d')
        self.socket.sendto(message, (self.broadcastDestination, 32108))
        print('broadcast Message sent.')

        if not self.isConnected and self.punchCount == 0:
            threading.Timer(self.reconnectDelay / 1000, self.send_broadcast).start()
            self.reconnectDelay += 1

    def send_enc(self, msg):
        if isinstance(msg, bytes):
            message = msg
        else:
            message = bytes.fromhex(msg)
        self.send(crypt_1.encrypt(message))

    def send(self, msg):
        if isinstance(msg, bytes):
            message = msg
        else:
            message = bytes.fromhex(msg)
        self.socket.sendto(message, (self.IP_CAM, self.PORT_CAM))

        if self.IP_DEBUG_MSG:
            self.socket.sendto(crypt_1.decrypt(message), (self.IP_DEBUG_MSG, 3301))

    def handle_packet(self, p, msg, rinfo):
        logmsg = ""
        if p['type'] == MSG_DRW:
            logmsg = f"Received {TYPE_DICT[p['type']]} size: {p['size']} channel: {p['channel']} index: {p['index']}"
        else:
            logmsg = f"Received {TYPE_DICT[p['type']]} size: {p['size']}"
        
        self.emit('debug', logmsg)

        # Reply to MSG_PUNCH to establish connection
        if p['type'] == MSG_PUNCH:
            print('MSG_PUNCH received')
            if self.punch_count < 5:
                self.punch_count += 1
                self.socket.sendto(msg, (rinfo[0], rinfo[1]))
                self.emit('log', f"Sent {TYPE_DICT[MSG_PUNCH]}")

        if p['type'] == MSG_P2P_RDY:
            print('MSG_P2P_RDY received')
            self.IP_CAM = rinfo[0]
            self.PORT_CAM = rinfo[1]

            if not self.is_connected:
                self.is_connected = True
                self.reconnect_delay = 500
                # Use threading.Timer to mimic JavaScript's setTimeout
                threading.Timer(0.5, lambda: self.emit('connected', rinfo[0], rinfo[1])).start()

        # Reply to MSG_ALIVE
        if p['type'] == MSG_ALIVE:
            print('MSG_ALIVE received')
            buf = bytearray(4)
            buf[0] = MCAM
            buf[1] = MSG_ALIVE_ACK
            buf[2:4] = (0).to_bytes(2, 'big')
            self.send_enc(buf)
            self.emit('log', f"Sent {TYPE_DICT[MSG_ALIVE_ACK]}")

        # Reply to MSG_CLOSE
        if p['type'] == MSG_CLOSE:
            print('MSG_CLOSE received')
            if self.is_connected:
                self.is_connected = False
                self.emit('disconnected', self.IP_CAM, self.PORT_CAM)
            buf = bytearray(4)
            buf[0] = MCAM
            buf[1] = MSG_ALIVE
            buf[2:4] = (0).to_bytes(2, 'big')
            for _ in range(12):
                self.send_enc(buf)
            self.emit('log', f"Sent {TYPE_DICT[MSG_ALIVE]}")

        # Handle MSG_DRW
        if p['type'] == MSG_DRW:
            # Send MSG_DRW_ACK
            buf = bytearray(10)
            buf[0] = MCAM
            buf[1] = MSG_DRW_ACK
            buf[2:4] = (6).to_bytes(2, 'big')
            buf[4] = 0xd1
            buf[5] = p['channel']
            buf[6:8] = (1).to_bytes(2, 'big')
            buf[8:10] = p['index'].to_bytes(2, 'big')
            self.send_enc(buf)

            # Handle CMD Response
            if p['channel'] == 0:
                print('CMD Response received')
                if p['data'].startswith(b'\x06\x0a'):
                    data = p['data'][8:]
                    _msg = data.decode('ascii')
                    self.emit('cmd', _msg)

            # Handle Video
            if p['channel'] == 1:
                # Handle MSG_DRW packet index overflow
                if p['index'] > 65400:
                    self.video_overflow = True

                if self.video_overflow and p['index'] < 65400:
                    self.last_video_frame = -1
                    self.video_overflow = False
                    self.video_boundaries.clear()
                    self.video_received = []

                if p['data'].startswith(b'\x55\xaa\x15\xa8\x03\x00'):
                    self.video_received[p['index']] = p['data'][0x20:]
                    self.video_boundaries.add(p['index'])
                else:
                    self.video_received[p['index']] = p['data']
                self.get_video_frame()

            # Handle audio
            if p['channel'] == 2:
                if self.last_audio_frame < p['index']:
                    raw = p['data'][0x20:] if p['data'].startswith(b'\x55\xaa\x15\xa8\xaa\x01') else p['data']
                    decoded = AdpcmDecoder.decode(raw)
                    self.last_audio_frame = p['index']
                    self.emit('audio_frame', {'frame': decoded, 'packet_index': p['index']})

    def send_cmd_packet(self, msg):
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

    def send_drw_packet(self, channel, data):
        buf = bytearray(len(data) + 8)
        buf[0] = MCAM
        buf[1] = MSG_DRW
        buf[2:4] = (len(data) + 4).to_bytes(2, 'big')
        buf[4] = MDRW
        buf[5] = channel
        buf[6:8] = (self.DRW_PACKET_INDEX & 0xFFFF).to_bytes(2, 'big')
        self.DRW_PACKET_INDEX += 1
        buf[8:] = data
        self.send_enc(buf)
        print(f'DRW packet sent (len: {len(buf)})')

    # ... (rest of the methods)
        


    # ... (continuing from the previous Python code)

    def parse_packet(self, buff):
        try:
            magic1 = buff[0]
            packet_type = buff[1]
            size = int.from_bytes(buff[2:4], byteorder='big')
            magic2 = buff[4]
            channel = buff[5]
            index = int.from_bytes(buff[6:8], byteorder='big')
            data = buff[8:]
        except Exception as e:
            print(f"Error parsing packet: {e}")
            return None

        return {
            'magic1': magic1,
            'type': packet_type,
            'size': size,
            'magic2': magic2,
            'channel': channel,
            'index': index,
            'data': data,
        }

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

    # ... (rest of the methods)