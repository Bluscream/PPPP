import argparse, logging, time, os, socket, threading, json, pathlib, signal, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pppp import PPPP

parser = argparse.ArgumentParser(description='[OPTIONS]...')
parser.add_argument('-v', '--version', action='version', version='1.0.0')
parser.add_argument('-p', '--port', type=int, default=3000, help='port number to use, default 3000')
parser.add_argument('-t', '--thisip', help='IP of the interface to bind')
parser.add_argument('-b', '--broadcastip', default='255.255.255.255', help='IP of the interface to bind')
parser.add_argument('-a', '--audio', action='store_true', help='Run with audio tunneling support (requires "speaker" npm package')
parser.add_argument('-r', '--reconnect', action='store_true', help='Automatically restart the connection once disconnected')
parser.add_argument('-pw', '--password', help='Require a password as a ?pw= query parameter to use the webserver')
parser.add_argument('-e', '--eval', action='store_true', help='eval mode, WARNING ⚠️ DO NOT USE THIS IN PRODUCTION')

options = parser.parse_args()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

p = None

def setup_pppp():
   global p
   if p:
       logger.info('pppp was already open, closing...')
       p.destroy()
       p = None
   p = PPPP(options)

   def log(msg):
       logger.info(msg)

   def connected(address, port):
       logger.info(f'Connected to camera at {address}:{port}')
       time.sleep(1)
       p.send_cmd_get_params()
       if options.audio:
           time.sleep(0.2)
           p.send_cmd_request_audio()
       time.sleep(0.1)
       p.send_cmd_request_video1()

   def disconnected(address, port):
       logger.info(f'Disconnected from camera at {address}:{port}')
       if options.reconnect:
           logger.info("Reconnecting ...")
           setup_pppp()

   def audio_frame(audio_frame):
       if options.audio:
           speaker.write(audio_frame.frame)

   def video_frame(video_frame):
       s = '--xxxxxxkkdkdkdkdkdk__BOUNDARY\r\n'
       s += 'Content-Type: image/jpeg\r\n\r\n'
       video_stream.write(bytes(s, 'utf-8'))
       video_stream.write(video_frame.frame)

   def error(err):
       logger.error(f'socket error: {err}')

   def cmd(msg):
       logger.info(msg)

   p.on('log', log)
   p.on('connected', connected)
   p.on('disconnected', disconnected)
   p.on('audioFrame', audio_frame)
   p.on('videoFrame', video_frame)
   p.on('error', error)
   p.on('cmd', cmd)

setup_pppp()

class RequestHandler(BaseHTTPRequestHandler):
   def do_GET(self):
        try:
            if self.path == '/favicon.ico':
                return
            print(f'[{self.client_address[0]}]: {self.command} {self.path}')
            parsed_url = urlparse(self.path)
            parsed_path = os.path.parse(parsed_url.path)
            query = parse_qs(parsed_url.query)
            if options.password and query.get('pw', [''])[0] != options.password:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'invalid password'}).encode())
                return
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'<!DOCTYPE html>\r\n<http><head></head><body><img src="/v.mjpg"></body></html>')
            elif self.path == '/v.mjpg':
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary="xxxxxxkkdkdkdkdkdk__BOUNDARY"')
                self.end_headers()
                video_stream.pipe(self.wfile)
            elif self.path == '/exit':
                os._exit(0)
            elif self.path == '/reconnect':
                setup_pppp()
            elif self.path.startswith('/func/'):
                if not options.eval:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': 'eval mode is disabled 🙄'}).encode())
                    return
                name = parsed_path.base
                args = ','.join([f'{k}={v}' for k, v in query.items()])
                eval_str = f'p.{name}({args})'
                print(eval_str)
                ret = eval(eval_str)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'ok', 'result': ret}).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'not found'}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'message': str(e)}).encode())

server: HTTPServer = None

def signal_handler(sig, frame):
    print('Shutting down server...')
    server.shutdown()
    server.server_close()
    if p:
        p.destroy()
    print('Server has been shut down. Exiting.')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    server_address = ('', options.port)
    server = HTTPServer(server_address, RequestHandler)
    print(f'Server running on port {options.port}...')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        signal_handler(None, None)