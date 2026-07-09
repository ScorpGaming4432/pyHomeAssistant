import webrtcvad
import pyaudio
import collections
import wave

RATE = 16000
FRAME_MS = 30  # webrtcvad only accepts 10, 20, or 30 ms
FRAME_SIZE = int(RATE * FRAME_MS / 1000)
CHANNELS = 1
FORMAT = pyaudio.paInt16

vad = webrtcvad.Vad(2)  # aggressiveness 0-3, higher = more strict about what counts as speech

def record_on_voice(padding_ms=300, silence_timeout_ms=800):
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                      input=True, frames_per_buffer=FRAME_SIZE)

    num_padding_frames = padding_ms // FRAME_MS
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    voiced_frames = []
    silence_frames = 0
    max_silence_frames = silence_timeout_ms // FRAME_MS

    print("Listening...")
    while True:
        frame = stream.read(FRAME_SIZE, exception_on_overflow=False)
        is_speech = vad.is_speech(frame, RATE)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = sum(1 for f, s in ring_buffer if s)
            if num_voiced > 0.8 * ring_buffer.maxlen:
                triggered = True
                print("Speech started")
                voiced_frames.extend(f for f, s in ring_buffer)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            if not is_speech:
                silence_frames += 1
                if silence_frames > max_silence_frames:
                    print("Speech ended")
                    break
            else:
                silence_frames = 0

    stream.stop_stream()
    stream.close()
    pa.terminate()

    return b"".join(voiced_frames)

def save_wav(data, path="output.wav"):
    wf = wave.open(path, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()

if __name__ == "__main__":
    audio = record_on_voice()
    save_wav(audio)
    print("Saved to output.wav")