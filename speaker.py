import pyaudio

class Speaker:
    def __init__(self, channels=1, bit_depth=16, sample_rate=8000):
        self.channels = channels
        self.bit_depth = bit_depth
        self.sample_rate = sample_rate
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=self.p.get_format_from_width(bit_depth // 8),
                                  channels=channels,
                                  rate=sample_rate,
                                  output=True)

    def write(self, data):
        self.stream.write(data)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

# Example usage:
# speaker = Speaker()
# speaker.write(b'\x00\x00' * 100)  # Play 100 samples of silence
# speaker.close()