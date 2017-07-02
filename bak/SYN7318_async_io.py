# -*- coding: utf-8 -*
import serial
import string
import binascii
import codecs
import sys

from array import array
from struct import pack
import time
import chunk
import threading

import asyncio
import RPi.GPIO as GPIO

BUSY_KEY = 17
# bcm编号方式
GPIO.setmode(GPIO.BCM)
# 输入模式
GPIO.setup(BUSY_KEY, GPIO.IN, GPIO.PUD_UP)

###############################SYN7318回传命令字定义############################
#模块通用回传
INIT_SUCCEED  = 0X41
RECEIVE_SUCCEED = 0X41
RECEIVE_FAILED = 0X45
IDEL_STATE = 0X4F
#状态查询
IAT_WAKE_UP_STATE = 0X42
PLAY_MP3_STATE = 0X49
UPDATE_DICT_STATE = 0X4B
TTS_STATE = 0X4E
#开始语音唤醒
WAKE_UP_SUCCEED = 0X21
WAKE_UP_ERROR = 0X22
#自定义唤醒名
CUSTOM_SET_WU_NAME_SUCCEED = 0X23
CUSTOM_SET_WU_NAME_FAILED = 0X24
#词条更新
UPDATE_DICT_SUCCEED = 0X31
UPDATE_DICT_FAILED = 0X32
#语音识别、三合一识别
IAT_ID_SUCCEED = 0X01
IAT_NO_ID_SUCCEED = 0X02
USER_MUTE_TIMEOUT = 0X03
USER_VOICE_TIMEOUT = 0X04
IAT_REFUSED1 = 0X05
IAT_REFUSED1 = 0X07
IAT_ERROR = 0X06

# 创建全局ThreadLocal对象:
is_idel_state = threading.local()
is_idel_state = False

#设置串口
ser = serial.Serial("/dev/ttyUSB0", 115200)
#ser = serial.Serial("COM6", 115200)

sound_people_dict = {'晓玲' : '[m3]', '尹小坚' : '[m51]', '易小强' : '[m52]', '田蓓蓓' : '[m53]', '唐老鸭' : '[m54]', '小燕子' : '[m55]'}
wake_up_name_dict = {'云宝' : 0, '小播' : 2, '百灵' : 4, '叮当管家' : 6, '百灵管家' : 7, '小播管家' : 8, '自定义' : 9}
#发送语音合成
#new_words: [m3] 晓玲(女声) [m51]尹小坚(男声) [m52]易小强(男声) [m53]田蓓蓓(女声) [m54]唐老鸭(效果器) [m55]小燕子(女童声)
#new_words: [s*] 语速值越小，语速越慢(0-10)
#new_words: [t*] 语调值越小，基频值越低(0-10)
#wart_for_complete 是否等待合成完毕
def serial_tts(new_words, wart_for_complete = True):
	global is_idel_state
	frame_head = b'\xFD'
	frame_command_type = b'\x01\x01'
	frame_text = new_words.encode('GBK')
	frame_length_h = bytes.fromhex('%.2X' %((len(frame_text) + 2)//255))
	frame_length_l = bytes.fromhex('%.2X' %((len(frame_text) + 2)%255))
	str_frame = frame_head + frame_length_h + frame_length_l + frame_command_type + frame_text
	ser.write(str_frame)
	if wart_for_complete:
		while not is_idel_state: #GPIO.input(BUSY_KEY):
			time.sleep(0.5)
	is_idel_state = False

#停止播放
def stop_play():
	frame_head = b'\xFD'
	frame_command_type = b'\x02'
	frame_length = b'\x00\x01'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)


#暂停播放
def pause_play():
	frame_head = b'\xFD'
	frame_command_type = b'\x03'
	frame_length = b'\x00\x01'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)
	
	
#恢复播放
def resume_play():
	frame_head = b'\xFD'
	frame_command_type = b'\x04'
	frame_length = b'\x00\x01'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)
	
	
#设置音量等级，默认为5
def serial_vol_level(vol_level):
	frame_head = b'\xFD'	
	frame_length = b'\x00\x02'	
	frame_command_type = b'\x05'
	frame_vol_level = bytes.fromhex('%.2X' %vol_level)
	str_frame = frame_head + frame_length + frame_command_type + frame_vol_level
	ser.write(str_frame)
	

#设置识别参数 开机默认：中距离模式：2级，用户静音上限为4000毫秒，用户语音上限为4000毫秒，拒识级别：4级（拒识率较低）
#recognition_distance (0x01:短距离0.2m; 0x02:中距离0.2-3m; 0x03:远距离3m)
#mute_time (1000-30000ms)
#voice_time (1000-6000ms)
#reject_level (0x01:拒识等级最高 --- 0x05:拒识等级最低)
def set_iat_par(recognition_distance, mute_time, voice_time, reject_level):
	frame_head = b'\xFD'
	frame_length = b'\x00\x06'
	frame_command = bytes.fromhex("1E")
	frame_recognition_distance = bytes.fromhex('%.2X' %recognition_distance)
	frame_mute_time_h = bytes.fromhex('%.2X' %(mute_time // 255))
	frame_mute_time_l = bytes.fromhex('%.2X' %(mute_time % 255))
	frame_voice_time_h = bytes.fromhex('%.2X' %(voice_time // 255))
	frame_voice_time_l = bytes.fromhex('%.2X' %(voice_time % 255))
	frame_reject_level = bytes.fromhex('%.2X' %reject_level)
	str_frame = frame_head + frame_length + frame_command + frame_recognition_distance + frame_mute_time_h + frame_mute_time_l + frame_voice_time_h + frame_voice_time_l + frame_reject_level
	ser.write(str_frame)
	
	
#开始识别
#dictionary_number: 词典编号： 0x00-0x09
def start_iat(dictionary_number):
	frame_head = b'\xFD'
	frame_length = b'\x00\x02'	
	frame_command_type = b'\x10'
	frame_dictionary_number = bytes.fromhex('%.2X' %dictionary_number)
	str_frame = frame_head + frame_length + frame_command + frame_dictionary_number
	ser.write(str_frame)


#三合一识别
#dictionary_number: 词典编号 0x00-0x09
#wake_up_name: 0：云宝 2: 小播 4：百灵 6：叮当管家 7：百灵管家 8：小播管家 9：大管家 31：自定义
#prompt_type: 提示音类型 0x00无提示音 0x01:文本类型 0x02:内置MP3类型 
#coded_format: 0x00：GB2312编码0x01：GBK编码0x02：BIG5编码0x03：Unicode小头0x04：Unicode大头
#开始0x02编号词典的三合一语音识别（唤醒名为云宝，唤醒后不播提示音，直接开始识别）
#0xFD 0x00 0x04 0x15 0x02 0x00 0x00
#开始0x01编号词典的三合一语音识别（唤醒名为百灵，唤醒后播GBK编码格式的文本提示音“嗯”，播完后开始识别）
#0xFD 0x00 0x070x15 0x01 0x04 0x01 0x01 0xE0 0xC5
#开始0x03编号词典的三合一语音识别（唤醒名为百灵，唤醒后播GBK编码格式的模块内置MP3提示音“D:\Mp3\Prompt_嘀.mp3”，播完后开始识别）
#0xFD 0x00 0x190x15 0x03 0x04 0x02 0x01 0x44 0x3A 0x5C 0x4D 0x70 0x33 0x5C 0x50 0x72 0x6F 0x6D 0x70 0x74 0x5F 0xE0 0xD6 0x2E 0x6D 0x70 0x33
def start_three_in_one_iat(dictionary_number, wake_up_name, prompt_type, coded_format, text):
	frame_head = b'\xFD'
	frame_length_h = bytes.fromhex('%.2X' %((len(text) + 5)//255))
	frame_length_l = bytes.fromhex('%.2X' %((len(text) + 5)%255))
	frame_command = bytes.fromhex("15")
	frame_dictionary_number = bytes.fromhex('%.2X' %dictionary_number)
	frame_wake_up_name = bytes.fromhex('%.2X' %wake_up_name)
	frame_prompt_type = bytes.fromhex('%.2X' %prompt_type)
	frame_coded_format = bytes.fromhex('%.2X' %coded_format)
	frame_text = text.encode('gbk')
	str_frame = frame_head + frame_length_h + frame_length_l + frame_command + frame_dictionary_number + frame_wake_up_name + frame_prompt_type + frame_coded_format + frame_text
	ser.write(str_frame)


#停止三合一识别
def stop_three_in_one_iat():
	frame_head = b'\xFD'
	frame_length = b'\x00\x01'	
	frame_command_type = b'\x16'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)


#启动唤醒
#wake_up_name: 0：云宝 2: 小播 4：百灵 6：叮当管家 7：百灵管家 8：小播管家 9：大管家 31：自定义
def start_wake_up(wake_up_name):
	frame_head = b'\xFD'
	frame_length = b'\x00\x01'	
	frame_command_type = b'\x51'
	frame_wake_up_name = bytes.fromhex('%.2X' %wake_up_name)
	str_frame = frame_head + frame_length + frame_command_type + frame_wake_up_name
	ser.write(str_frame)
	
	
#停止唤醒
def stop_wake_up():
	frame_head = b'\xFD'
	frame_length = b'\x00\x01'	
	frame_command_type = b'\x52'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)

#状态查询
def status_inquiry():
	count = 0
	ser.flushInput() #qint kong
	frame_head = b'\xFD'
	frame_length = b'\x00\x01'	
	frame_command_type = b'\x21'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)
	

#设置指示灯
#indicator_light_statu: (0x00录音灯在语音识别时不会亮 0x01录音灯在语音识别时会亮起)
def set_indicator_light(indicator_light_statu):
	frame_head = b'\xFD'
	frame_length = b'\x00\x02'
	frame_command_type = b'\x23'
	frame_wake_up_name = bytes.fromhex('%.2X' %indicator_light_statu)
	str_frame = frame_head + frame_length_h + frame_length_l + frame_command_type + frame_wake_up_name
	ser.write(str_frame)

#开始录音
def start_record():
	frame_head = b'\xFD'
	frame_length = b'\x00\x01'	
	frame_command_type = b'\x25'
	str_frame = frame_head + frame_length + frame_command_type
	ser.write(str_frame)



def get_entry_command_id(frame_data):
	entry_id = frame_data[0] * 256 + frame_data[1]
	command_id = frame_data[2] * 256 + frame_data[3]
	return entry_id, command_id
	
def get_command_id(frame_data):
	command_id = frame_data[0] * 256 + frame_data[1]
	return command_id

def analysis_command_data(frame_command, frame_data):
	global is_idel_state
	#lock.acquire()
	try:		
		if frame_command == RECEIVE_SUCCEED:
			
			is_receive_succeed = True
			print('receive_succeed')
		elif frame_command == IDEL_STATE:
			is_idel_state = True
			print('idel_state')
		elif frame_command == WAKE_UP_SUCCEED:
			is_wake_up_succeed = True
			print('wake_up_succeed')
		elif frame_command == WAKE_UP_ERROR:
			is_wake_up_succeed = False
			print('wake_up_failed')
		elif frame_command == IAT_ID_SUCCEED:
			is_iat_id_succeed = True
			get_entry_command_id(frame_data)
		elif frame_command == IAT_NO_ID_SUCCEED:
			is_iat_no_id_succeed = True
			get_command_id(frame_data)
		elif frame_command == USER_MUTE_TIMEOUT:		
			print('user mute timeout')
		elif frame_command == USER_VOICE_TIMEOUT:
			print('user voice timeout')
		elif frame_command == IAT_REFUSED1 or frame_command == IAT_REFUSED2:
			print('iat refused')
		elif frame_command == IAT_ERROR:
			print('iat error')
		elif frame_command == RECEIVE_FAILED:
			is_receive_succeed = False
		elif frame_command == IAT_WAKE_UP_STATE or frame_command == PLAY_MP3_STATE or frame_command == UPDATE_DICT_STATE or frame_command == TTS_STATE:
			is_idel_state = False
			modle_state = frame_command
		elif frame_command == INIT_SUCCEED:
			is_init_state = True
	finally:
		pass
		#lock.release()

@asyncio.coroutine
def receive_status():
	is_frame_start = 0
	is_frame_length = 1
	is_frame_length = 2
	is_frame_command = 3
	is_frame_end = 4
	frame_status = -1
	while True:
		count = ser.inWaiting()
		if count  > 0:			
			recv = ser.read(count)
			print('recv=',recv)
			for i in range(0, count):
				if recv[i] == ord('\xfc') and frame_status == -1:
					frame_status = is_frame_start
					frame_length_str = []
					frame_data = []
					continue
				if frame_status == is_frame_start:
					frame_length_str.append(recv[i])
					if len(frame_length_str) >= 2:
						frame_status = is_frame_length
						frame_length = frame_length_str[0] * 256 + frame_length_str[1]
					continue
				elif frame_status == is_frame_length:
					frame_command = recv[i]
					if frame_length > 6:
						frame_status = -1
						print('receive error!')
						continue
					elif frame_length > 1 and frame_length <= 6:
						frame_status = is_frame_command
						continue
					elif frame_length == 1:						
						frame_status = is_frame_end
				elif frame_status == is_frame_command:
					frame_data.append(recv[i])				
					if len(frame_data) >= frame_length - 1:
						frame_status = is_frame_end
					else:
						continue
			
				if frame_status == is_frame_end:					
					#print('command = ', frame_command)
					#print('data = ', frame_data)
					analysis_command_data(frame_command, frame_data)
					frame_status = -1
		
		time.sleep(0.01)


try:
	# 获取EventLoop:
	loop = asyncio.get_event_loop()
	# 执行coroutine
	loop.run_until_complete(receive_status())
	
	serial_vol_level(1)
	time.sleep(0.5);
	serial_tts(sound_people_dict['易小强'])   #yi xiao qiang
	text_count = 0
	while text_count <= 10:
		text = '测试' + str(text_count)
		serial_tts(text)
		text_count += 1;
		time.sleep(0.01)
	
except KeyboardInterrupt:
	print ('thread ended.')
