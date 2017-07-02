# -*- coding: utf-8 -*
import serial
import string
import binascii
import ruting_robot
import os
import codecs

import sys
import signal
import ctypes

from array import array
from struct import pack
import wave
import time
import chunk

from SYN7318 import *

CHANNELS = 1
RATE = 16000
FRAME_TYPE = 16
CHUNK_DURATION_MS = 20       # supports 10, 20 and 30 (ms)

libpcmpath = os.path.join(os.getcwd(),"record/libalsa_record.so")
print(libpcmpath)
libpcm = ctypes.CDLL(libpcmpath)

def main():	
	while True:
		
		f = open("iat_result.txt", "rb")
		words = f.read().decode("utf-8")
		f.close()
		print(words[0:15])		
		new_words = ruting_robot.robot_main(words[0:15])
		print(new_words)
		#serial_tts('[m52]')
		ser.flushInput()
		status = False
		while not status:
			time.sleep(0.1)
			status = status_inquiry()
		serial_tts(new_words)
		status = False
		while not status:
			time.sleep(1)
			status = status_inquiry()

if __name__ == '__main__':
	try:
		time.sleep(4)
		serial_vol_level(1)
		time.sleep(1)
		serial_tts('[m52]')
		main()
	except KeyboardInterrupt:
		if ser != None:
			ser.close()
