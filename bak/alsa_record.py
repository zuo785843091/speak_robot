#!/usr/bin/python3
#
from ctypes import *
import time
import ctypes
import os
import sys
import wave
import pyaudio
import numpy as np
import struct

CAPTURE_DEVICE = "plughw:1,0"
chunk_size = 16000
frames_size = 32
sample_rate = 16000
channels = 1
format_type = 16
filename = "alsa_test.wav"
period = 20   #20ms
#format_type = pyaudio.paInt16


frames = (ctypes.c_short * chunk_size)()
voice_data = (ctypes.c_int * 2)()
libpcmpath = os.path.join(os.getcwd(),"record/libalsa_record.so")
print(libpcmpath)
libpcm = ctypes.CDLL(libpcmpath)

print("capture_handle = record_config_init")
capture_handle = libpcm.record_init(sample_rate, channels, format_type,  "plughw:1,0")

print("voice_init")
libpcm.voice_init(period, sample_rate, ctypes.pointer(voice_data), capture_handle)
print("voice_data", voice_data[:])
TE = int(1.5 * voice_data[0])
TZ = 20
print("T= %d %d\n", TE, TZ)
TO = voice_data[0]
while(True):
	active = libpcm.is_speech(period, sample_rate, TZ, TE, TO, capture_handle)
	sys.stdout.write('1' if active else '_')
	

libpcm.point_vad(period, sample_rate, capture_handle)


totle_size = libpcm.alsa_read_frame(chunk_size,  ctypes.pointer(frames), capture_handle)
print(frames[:])
data_f = []
for i in range(1, chunk_size):
	data_f.append(struct.pack('<h', frames[i]))
#print(data_f)
'''
#data_f = frames.tolist()
data_0 = frames[:]
print(data_0)
print("\n", type(frames))
data_1 =  struct.pack('<hh', data_0[:])
print(data_1)
#print(libpcm.record(8000))
'''
libpcm.snd_pcm_close(capture_handle)
wf = wave.open(filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(2)
wf.setframerate(sample_rate)
wf.writeframes(b''.join(data_f))
wf.close()

