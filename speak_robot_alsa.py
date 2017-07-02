#!/usr/bin/python3
# -*- coding: utf-8 -*
import string
import binascii
import ruting_robot
import os
import codecs
import socket
import fcntl

import sys
import signal
import ctypes

from array import array
import struct
import wave
import time
import chunk

from SYN7318 import *

CHANNELS = 1
RATE = 16000
FRAME_TYPE = 16
CHUNK_DURATION_MS = 20       # supports 10, 20 and 30 (ms)

KEY1 = 27                    #外部按键

is_network = False
is_eth0_up = False


libpcmpath = os.path.join(os.getcwd(),"record/libalsa_record.so")
libpcm = ctypes.CDLL(libpcmpath)

libnetworkpath = os.path.join(os.getcwd(),"network/libnetwork.so")
libnetwork = ctypes.CDLL(libnetworkpath)

key_status = 0

def check_network():
	net_status = os.system('ping www.baidu.com -c 2')
	if net_status == 0:
		return True
	else:
		return False

def KEY1_callback(key_num):
	global key_status
	t0 = time.time()
	t1 = 0
	
	while GPIO.input(KEY1) and t1 < 3:
		t1 = time.time() - t0

	if t1 >= 3:
		key_status = 1 #长按
	else:
		key_status = 2 #短按
	print('这是一个边缘事件回调函数！')

def robot_online():
	is_get_sentence = libpcm.alsa_vad(RATE, FRAME_TYPE, CHANNELS, CHUNK_DURATION_MS)
	if is_get_sentence == 1:
		os.system('./Linux_voice_1.109/bin/iat_sample')
	
		f = open("iat_result.txt", "rb")
		words = f.read().decode("utf-8")
		f.close()
		print(words[0:15])
		
		if words != '\x00':
			new_words = ruting_robot.robot_main(words[0:15])		
			print(new_words)
			while GPIO.input(BUSY_KEY):
				time.sleep(1)
			serial_tts(new_words, False)

def robot_offline():
	pass


def robot_init():
	serial_vol_level(1)
	time.sleep(0.5);
	serial_tts(sound_people_dict['易小强'], False)   #yi xiao qiang
	is_network = check_network()
	#os.system('sudo ifconfig eth0 down')
	is_eth0_up = libnetwork.get_link_eth(b'eth0')


def main():
	GPIO.setup(KEY1,GPIO.IN,GPIO.PUD_UP)
	GPIO.add_event_detect(KEY1, GPIO.FALLING, KEY1_callback, 200) # 在通道上添加上升临界值检测 GPIO.RISING、GPIO.FALLING、GPIO.BOTH
	while key_status == 0:
		robot_online()


if __name__ == '__main__':
	try:
		robot_init()
		main()
	except KeyboardInterrupt:
		if ser != None:
			ser.close()






'''
#软件合成播放
os.system('sudo ./Linux_voice_1.109/bin/tts_sample %s' %new_words)
os.system('mplayer tts_result.wav')                                #前台播放
#os.system('mplayer tts_result.wav < /dev/null > /dev/null 2>&1 &') #后台播放
'''
