# -*- coding: utf-8 -*
import serial
import string
import binascii
import ruting_robot
import os
import codecs
import pyaudio_record

#初始化串口
ser = serial.Serial("/dev/ttyUSB0", 115200)


#发送到串口合成语音
def serial_tts(new_words):
	frame_head = bytes.fromhex("FD")
	frame_command_type = bytes.fromhex("01 01")
	frame_text = new_words.encode('gbk')
	frame_length_h = bytes.fromhex("00")
	frame_length_l = bytes.fromhex('%.2X' %(len(frame_text) + 2))
	str_frame = frame_head + frame_length_h + frame_length_l + frame_command_type + frame_text
	ser.write(str_frame)

def serial_vol_level(vol_level):
	frame_head = bytes.fromhex("FD")
	frame_length = bytes.fromhex("00 02")
	frame_command = bytes.fromhex("05")
	frame_vol_level = bytes.fromhex('%.2X' %vol_level)
	str_frame = frame_head + frame_length + frame_command + frame_vol_level
	ser.write(str_frame)
	
def main():
	while True:
		#os.system('arecord -D "plughw:1" -f S16_LE -r 16000 -d 15 wav/iflytek02.wav')
		pyaudio_record.record_sound()
		os.system('./Linux_voice_1.109/bin/iat_sample')
		
		f = open("iat_result.txt", "rb")
		words = f.read().decode("utf-8")
		f.close()
		print(words[0:15])
		
		new_words = ruting_robot.robot_main(words[0:15])		
		print(new_words)
		serial_tts(new_words)
		'''
		#软件合成播放
		os.system('sudo ./Linux_voice_1.109/bin/tts_sample %s' %new_words)
		os.system('mplayer tts_result.wav')                                #前台播放
		#os.system('mplayer tts_result.wav < /dev/null > /dev/null 2>&1 &') #后台播放
		'''
if __name__ == '__main__':
	try:
		serial_vol_level(1)
		main()
	except KeyboardInterrupt:
		if ser != None:
			ser.close()
