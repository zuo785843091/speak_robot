# -*- coding: utf-8 -*
import pyaudio
import wave

def record_sound():
	#Pyaudio Â¼Òô²ÎÊý
	chunk_size = 160
	sample_rate = 16000
	seconds = 10
	filename = "wav/iflytek02.wav"
	channels = 1
	format_type = pyaudio.paInt16
	
	p = pyaudio.PyAudio()
	
	stream = p.open(format=format_type,
									channels=channels,
									rate=sample_rate,
									input=True,
									frames_per_buffer=chunk_size)
	
	print("Speak now: ", seconds)
	
	frames = []
	
	for i in range(0, int(sample_rate / chunk_size * seconds)):
		data = stream.read(chunk_size, False)
		#print(" ", len(data))
		#print("\n type \n", type(data))
		frames.append(data)
		#if i%int(sample_rate/chunk_size) == 0:
		#	print(seconds - round(i/(sample_rate/chunk_size)), " seconds remaining")
	
	print("Finished")
	
	stream.stop_stream()
	stream.close()
	p.terminate()
	
	wf = wave.open(filename, 'wb')
	wf.setnchannels(channels)
	wf.setsampwidth(p.get_sample_size(format_type))
	wf.setframerate(sample_rate)
	wf.writeframes(b''.join(frames))
	wf.close()

#record_sound(seconds, chunk_size, sample_rate, filename, channels, format_type)
