# -*- coding: utf-8 -*
import string
import binascii
import serial
import time

ser = serial.Serial("/dev/ttyUSB0", 115200)

def main():
	str_f = bytes.fromhex('FD 00 0A 01 01')
	ser.write(str_f)
	ser.write("语音天下".encode('gbk'))
	while True:
	# 获得接收缓冲区字符
		count = ser.inWaiting()
		if count != 0:
			# 读取内容并回显
			recv = ser.read(count)
			print(recv)
			# ser.write(recv)
			# 清空接收缓冲区
			ser.flushInput()
		# 必要的软件延时
		time.sleep(0.1)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		if ser != None:
			ser.close()
