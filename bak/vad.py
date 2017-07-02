# -*- coding: utf-8 -*
import collections
import sys
import os
import signal
import ctypes

from array import array
from struct import pack
import wave
import time
import chunk


CHANNELS = 1
RATE = 16000
CHUNK_DURATION_MS = 20       # supports 10, 20 and 30 (ms)
PADDING_DURATION_MS = 1500   # 1 sec jugement
CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # chunk to read
CHUNK_BYTES = CHUNK_SIZE * 2  # 16bit = 2 bytes, PCM
NUM_PADDING_CHUNKS = int(PADDING_DURATION_MS / CHUNK_DURATION_MS)
# NUM_WINDOW_CHUNKS = int(240 / CHUNK_DURATION_MS)
NUM_WINDOW_CHUNKS = int(240 / CHUNK_DURATION_MS)  # 400 ms/ 30ms  ge
NUM_WINDOW_CHUNKS_END = NUM_WINDOW_CHUNKS * 5

START_OFFSET = int(NUM_WINDOW_CHUNKS * CHUNK_DURATION_MS * 0.5 * RATE)

got_a_sentence = False
leave = False

def handle_int(sig, chunk):
    global leave, got_a_sentence
    leave = True
    got_a_sentence = True


def record_to_file(path, data, sample_width):
    "Records from the microphone and outputs the resulting data to 'path'"
    # sample_width, data = record()
    data = pack('<' + ('h' * len(data)), *data)
    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 32767  # 16384
    times = float(MAXIMUM) / max(abs(i) for i in snd_data)
    r = array('h')
    for i in snd_data:
        r.append(int(i * times))
    return r

signal.signal(signal.SIGINT, handle_int)

frames = (ctypes.c_short * CHUNK_SIZE)()
voice_data = (ctypes.c_int * 2)()
libpcmpath = os.path.join(os.getcwd(),"record/libalsa_record.so")
print(libpcmpath)
libpcm = ctypes.CDLL(libpcmpath)

print("capture_handle = record_config_init")
capture_handle = libpcm.record_init(RATE, CHANNELS, 16,  "plughw:1,0");
print("voice_init")
libpcm.voice_init(CHUNK_DURATION_MS, RATE, ctypes.pointer(voice_data), capture_handle)
print("voice_data", voice_data[:])
TE = int(1.5 * voice_data[0])
TZ = 20
print("T= %d %d\n", TE, TZ)
TO = voice_data[0]

while not leave:
    ring_buffer = collections.deque(maxlen=NUM_PADDING_CHUNKS)
    triggered = False
    voiced_frames = []
    ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
    ring_buffer_index = 0

    ring_buffer_flags_end = [0] * NUM_WINDOW_CHUNKS_END
    ring_buffer_index_end = 0
    buffer_in = ''
    # WangS
    raw_data = array('h')
    index = 0
    start_point = 0
    StartTime = time.time()
    print("* recording: ")
    
    while not got_a_sentence and not leave:

        #chunk = stream.read(CHUNK_SIZE)
        # add WangS
        #raw_data.extend(array('h', chunk))
        index += CHUNK_SIZE
        TimeUse = time.time() - StartTime

        active = libpcm.is_speech(CHUNK_DURATION_MS, RATE, TZ, TE, TO, capture_handle)

        sys.stdout.write('1' if active else '_')
        ring_buffer_flags[ring_buffer_index] = 1 if active else 0
        ring_buffer_index += 1
        ring_buffer_index %= NUM_WINDOW_CHUNKS

        ring_buffer_flags_end[ring_buffer_index_end] = 1 if active else 0
        ring_buffer_index_end += 1
        ring_buffer_index_end %= NUM_WINDOW_CHUNKS_END

        # start point detection
        if not triggered:
            ring_buffer.append(chunk)
            num_voiced = sum(ring_buffer_flags)
            if num_voiced > 0.9 * NUM_WINDOW_CHUNKS:
                sys.stdout.write(' Open ')
                triggered = True
                start_point = index - CHUNK_SIZE * 20  # start point
                # voiced_frames.extend(ring_buffer)
                ring_buffer.clear()
        # end point detection
        else:
            # voiced_frames.append(chunk)
            ring_buffer.append(chunk)
            num_unvoiced = NUM_WINDOW_CHUNKS_END - sum(ring_buffer_flags_end)
            if num_unvoiced > 0.90 * NUM_WINDOW_CHUNKS_END: # or TimeUse > 10
                sys.stdout.write(' Close ')
                triggered = False
                got_a_sentence = True

        sys.stdout.flush()

    sys.stdout.write('\n')
    # data = b''.join(voiced_frames)

    libpcm.snd_pcm_close(capture_handle)
    print("* done recording")
    got_a_sentence = False

    # write to file
    raw_data.reverse()
    for index in range(start_point):
        raw_data.pop()
    raw_data.reverse()
    #raw_data = normalize(raw_data)
    record_to_file("recording.wav", raw_data, 2)
    leave = True
