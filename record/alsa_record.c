#include "pcm_alsa.h"
#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>
#include<sys/types.h>
#include<sys/stat.h>
#include<fcntl.h>

//wav 文件头数据结构
#define ID_RIFF     0x46464952
#define ID_WAVE     0x45564157
#define ID_FMT      0x20746d66
#define ID_DATA     0x61746164

#define FORMAT_PCM  1

#define fix_min_max(m, min, max) (m < min ? min : m > max ? max : m)

pthread_mutex_t alsa_cap_mutex;

struct wav_header {
    /* RIFF WAVE Chunk */
    uint32_t riff_id;       /*固定字符串　RIFF*/
    uint32_t riff_sz;       /**/
    uint32_t riff_fmt;
    /* Format Chunk */
    uint32_t fmt_id;
    uint32_t fmt_sz;
    uint16_t audio_format;
    uint16_t num_channels;
    uint32_t sample_rate;
    uint32_t byte_rate;     /* sample_rate * num_channels * bps / 8 */
    uint16_t block_align;   /* num_channels * bps / 8 */
    uint16_t bits_per_sample;
    /* Data Chunk */
    uint32_t data_id;
    uint32_t data_sz;
};

struct vad_parameter{

	int sample_rate;                        //采样率
	int format_type;                        //采样格式 16bit
	int num_channels;                       //录音通道数量
	int chunk_duration_ms;                  //窗口时间
	int chunk_size;                         //窗口数据量	 
	int chunk_bytes;                        //窗口bytes数量	
	int num_window_chunks_start;             //开始端点语音窗口数量
	int num_window_chunks_end;              //结束端点非语音窗口数量
	
	float start_voice_parameter;            //开始端点乘积因子
	float end_voice_parameter;              //结束端点乘积因子
	int mute_time;                          //静音时间
	int voice_time;                         //语音时间
	
	int TE_MIN;                             //门限最小能量值
	int TE_MAX;                             //门限最大能量值
	int TZ_MIN;                             //门限最小过零率
	int TZ_MAX;                             //门限最大过零率
	int TO_MIN;                             //过零率幅度最大值
	int TO_MAX;                             //过零率幅度最小值
};

typedef struct wav_header WAV_HEADER_T;
typedef struct vad_parameter VAD_PARAMETER_T;

int add_wav_head(int fd, WAV_HEADER_T* hdr, uint32_t totle_size)
{
    /* 回到文件头,重新更新音频文件大小 */
    lseek(fd, 0, SEEK_SET);

    /*填充文件头*/
    //RIFF WAVE Chunk
    hdr->riff_id = ID_RIFF;                 //固定格式
    hdr->riff_sz = totle_size + 36;         //Filelength=totle_size + 44 － 8
    hdr->riff_fmt = ID_WAVE;
    //Format Chunk
    hdr->fmt_id = ID_FMT;
    hdr->fmt_sz = 16;                       //一般为16，如果18要附加信息
    hdr->audio_format = FORMAT_PCM;         //编码方式：一般为１
    hdr->num_channels = 1;                  //声道数
    hdr->sample_rate = 16000;               //采样频率
    hdr->bits_per_sample = 16;              //样本长度
    hdr->byte_rate = hdr->sample_rate * hdr->num_channels * hdr->bits_per_sample / 8;         //每秒所需的字节数  采样频率×通道数×样本长度
    hdr->block_align = hdr->num_channels * hdr->bits_per_sample / 8;                          //数据块对齐单位(每个采样需要的字节数)
    //Data Chunk
    hdr->data_id = ID_DATA;
    hdr->data_sz = totle_size;

    if (write(fd, hdr, sizeof(WAV_HEADER_T)) != sizeof(WAV_HEADER_T)) {
        fprintf(stderr, "arec: cannot write header\n");
        return -1;
    }
    fprintf(stderr,"arec: %d ch, %ld hz, %d bit, %s\n",
        hdr->num_channels, hdr->sample_rate, hdr->bits_per_sample,
        hdr->audio_format == FORMAT_PCM ? "PCM" : "unknown");

     return fd;
}

/*******************************************
函数功能：在固定路径下创建文件
参数说明：
返回说明：文件语句柄
********************************************/
int create_and_open_file(const char* path)
{
    int fd = -1;
    // O_TRUNC:　如果文件存在并以只读或读写打开，则将其长度截短为０
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0664);
    if(fd < 0) {
        fprintf(stderr, "arec: cannot open '%d'\n", fd);
        return -1;
    }
    return fd;
}

int write_info_to_file(int fd, short* buf, int frame, int totle_size)
{
    int rc = write(fd, buf, 2 * frame);
    if (rc != 2 * frame)
      fprintf(stderr,
              "short write: wrote %d bytes\n", rc);
		return totle_size + frame;
}

snd_pcm_t *record_init(u32 rate, u32 channles, u8 sample, const char* dev_name)
{
		snd_pcm_t *capture_handle;//会语句柄
		capture_handle = record_config_init(rate, channles, sample, CAPTURE_DEVICE);
		return capture_handle;
}

int alsa_read_frame(int frame, short *f_buf, snd_pcm_t *capture_handle)
{
	int err = -1;

	if((err = snd_pcm_readi(capture_handle, f_buf, frame)) != frame) {
		if (err == -EPIPE) {
		  /* EPIPE means overrun */
		  fprintf(stderr, "overrun occurred\n");
		  snd_pcm_prepare(capture_handle);
		} else if (err < 0) {
		  fprintf(stderr,
				  "error from read: %s\n",
				  snd_strerror(err));
		} else {
		  fprintf(stderr, "short read, read %d frames\n", err);
		}
	}
	return (err);
}

int alsa_read_chunk(int chunk_duration_ms, int sample_rate, short *f_buf, snd_pcm_t *capture_handle)
{
		int err = -1;
		int per_frames = sample_rate / 1000;
		int totle_frames = chunk_duration_ms * per_frames;
		int i = 0;
		for (i = 0; i < chunk_duration_ms; i++){
				err = alsa_read_frame(per_frames, &f_buf[i*per_frames], capture_handle);
		}
		return err;
}

//录制音频
u32 record(u32 loops)
{
    int fd = -1;
    int err = -1;
    WAV_HEADER_T* hdr = (WAV_HEADER_T *)malloc(sizeof(WAV_HEADER_T));
    
    u32 totle_size = 0;         /*记录总量*/
    int frame = 2;              /*　帧大小　＝　量化单位×通道数　/ 字节位数　*/
    short buf[frame];
    //buf =(short*)malloc(2*sizeof(short));
    int start_sec = 0;
    snd_pcm_t *capture_handle;//会语句柄

    //初始化声卡配置
    capture_handle = record_config_init(16000, 1, 16, CAPTURE_DEVICE);
    //录音开始
    printf("Ready to capture frame...\n");

    //在指定路径打开或创建固定音频文件　0664
    fd = create_and_open_file("test.pcm");
    printf("Start to record...\n");
    //start_sec = get_sec();
    while(loops--)                      //这里到时修正成　后端点检测
    {
        //bzero(buf,16);
        if((err = snd_pcm_readi(capture_handle, buf, frame)) != frame)
        {
            fprintf(stderr, "read from audio interface failed(%s)\n",
            snd_strerror(err));
            exit(1);
        }
        totle_size = write_info_to_file(fd,  buf, frame, totle_size);
        //printf(" %d : %d", buf[0], buf[1]);
    }
	printf("tltle_size = %d\n", totle_size);
    //加入音频头
    fd  = add_wav_head(fd, hdr, totle_size);

    //关闭文件
    snd_pcm_close(capture_handle);
    //free(buf);
    close(fd);
    //printf("Use %d seconds!\n",get_sec()-start_sec);
    return totle_size;
}

/***********************************
函数功能：
    使用矩形窗口函数计算短时能量

参数说明：
        audioFramePtr: 音频帧
        win_len: 滑动窗口长度
返回值：
        每段帧的能量值
************************************/
int energyPerSampleUseRectangle(short* audio_frame_ptr, int win_len)
{
		unsigned int energy_int = 0;
    double energy = 0.2f; //保留小数点后两位
    short sample;
    int i = 0;
    for (i = 0; i<win_len; i++){
        sample = *(audio_frame_ptr + i);
        //energy += sample * sample;
        energy_int += abs(sample);
    }
    energy_int = energy_int / win_len;
    //energy = (double)10 * log(energy);
    return energy_int;
}

/****************************************
函数功能：
    使用矩形窗口函数计算短时过零率

参数说明：
        audioFramePtr: 音频帧
        win_len: 滑动窗口长度
返回值：
        每段帧的过零率
***************************************/
int zeroPointPerSampleUseRectangle(short* audio_frame_ptr, int win_len, int T)
{
    int zeroPoint = 0;
    short sample = 0;
    int i = 0;
    for (i = 0; i<win_len-1; i++){
    		if ((*(audio_frame_ptr + i)) * (*(audio_frame_ptr + i + 1)) < 0 && abs(*(audio_frame_ptr + i) - *(audio_frame_ptr + i + 1)) > T){
    				zeroPoint++;
    		}
    }
    return zeroPoint;
}

int is_speech(int chunk_size, int TZ, int TE, int TO, short *chunk, snd_pcm_t *capture_handle)
{
		int energy_int = 0;
		int zeroPoint = 0;
		int active = 0;

		energy_int = energyPerSampleUseRectangle(chunk, chunk_size);
		zeroPoint = zeroPointPerSampleUseRectangle(chunk, chunk_size, TO);

		active = (energy_int >= TE && zeroPoint >= TZ) ? 1 : 0;
		return active;
}

void voice_init(int period, int sample_rate, int *voice_data, snd_pcm_t *capture_handle)
{
		int per_frames = sample_rate / 1000;
		int totle_frames = period * per_frames;
		short f_buf[totle_frames];
		int energy_int = 0;
		int zeroPoint = 0;
		int k = 0;
		int i = 0;
		for (k = 0; k < 5; k++){
				for (i = 0; i < period; i++){
						alsa_read_frame(per_frames, &f_buf[i*per_frames], capture_handle);
				}
				energy_int += energyPerSampleUseRectangle(f_buf, totle_frames);
				zeroPoint += zeroPointPerSampleUseRectangle(f_buf, totle_frames, 100);
		}
		voice_data[0] = energy_int / 5;
		voice_data[1] = zeroPoint / 5;
}

int array_sum(char *array, int size)
{
	int i = 0;
	int sum = 0;
	for (i == 0; i < size; i++){
		sum += array[i];
	}
	return sum;
}

int vad(VAD_PARAMETER_T *vad_par, snd_pcm_t *capture_handle)
{
	int fd = -1;
	int i = 0;
    int index = 0;
    int active = 0;
    int time_start = 0;
    int time_totle = 0;
	int num_voiced = 0;
	int num_unvoiced = 0;
	uint32_t totle_size = 0;
	int got_a_sentence = 0;
	int triggered = 0;	
    int ring_buffer_index = 0;
    int ring_buffer_index_end = 0;
    int per_chunk_point = 0;
    
    int voice_data[2];
	short chunk[vad_par->chunk_size];
	short per_chunk[vad_par->num_window_chunks_start * (vad_par->chunk_size)];
	char ring_buffer_flags[vad_par->num_window_chunks_start];
    char ring_buffer_flags_end[vad_par->num_window_chunks_end];
    WAV_HEADER_T* hdr = (WAV_HEADER_T *)malloc(sizeof(WAV_HEADER_T));
    
    memset(ring_buffer_flags, 0, sizeof(char)*vad_par->num_window_chunks_start);
    memset(ring_buffer_flags_end, 0, sizeof(char)*vad_par->num_window_chunks_end);
    
    //在指定路径打开或创建固定音频文件　0664
    fd = create_and_open_file("wav/iflytek02.wav");

    printf("* recording: \n");
    voice_init(vad_par->chunk_duration_ms, vad_par->sample_rate, voice_data, capture_handle);
	int TE = fix_min_max(1.5 * voice_data[0], vad_par->TE_MIN, vad_par->TE_MAX);
	int TZ = fix_min_max(1.5 * voice_data[1], vad_par->TZ_MIN, vad_par->TZ_MAX);
	int TO = fix_min_max(voice_data[0],       vad_par->TO_MIN, vad_par->TO_MAX);
	printf("voice_data= %d %d\n", voice_data[0], voice_data[1]);
    printf("Tez= %d %d %d\n", TE, TZ, TO);
	while (!got_a_sentence){
		//alsa_read_chunk(CHUNK_DURATION_MS, RATE, chunk, capture_handle);
		alsa_read_frame(vad_par->chunk_size, chunk, capture_handle);
		active = is_speech(vad_par->chunk_size, TZ, TE, TO, chunk, capture_handle);
		index += vad_par->chunk_size;
		write(0, active == 1 ? "1" : "_", 1);
		time_totle += vad_par->chunk_duration_ms;
		if (!triggered){
			per_chunk_point = ring_buffer_index * vad_par->chunk_size;
			for (i = 0; i < vad_par->chunk_size; i++){
				per_chunk[per_chunk_point + i] = chunk[i];
			}
		}
				
		ring_buffer_flags[ring_buffer_index] = (active == 1 ? 1 : 0);
		ring_buffer_index += 1;
		ring_buffer_index %= vad_par->num_window_chunks_start;
		
		ring_buffer_flags_end[ring_buffer_index_end] = (active == 1 ? 1 : 0);
		ring_buffer_index_end += 1;
		ring_buffer_index_end %= vad_par->num_window_chunks_end;

		if (!triggered){
			num_voiced = array_sum(ring_buffer_flags, vad_par->num_window_chunks_start);
			if (num_voiced > vad_par->start_voice_parameter * vad_par->num_window_chunks_start){
				time_start = time_totle;
				write(0, "OPEN", 4);
				totle_size = write_info_to_file(fd, &per_chunk[ring_buffer_index * vad_par->chunk_size], (12 - ring_buffer_index) * (vad_par->chunk_size), totle_size);
				totle_size = write_info_to_file(fd, per_chunk, (ring_buffer_index) * (vad_par->chunk_size), totle_size);
				triggered = 1;
			}
			if (time_totle > vad_par->mute_time){
				fd = add_wav_head(fd, hdr, totle_size);
				free(hdr);
				close(fd);
				return 0;
			}
		}else{
			num_unvoiced = vad_par->num_window_chunks_end - array_sum(ring_buffer_flags_end, vad_par->num_window_chunks_end);
			if ((num_unvoiced > (vad_par->end_voice_parameter * vad_par->num_window_chunks_end)) || (time_totle - time_start > vad_par->voice_time)){
				write(0, "CLOSE", 4);
				triggered = 0;
				got_a_sentence = 1;
			}
			totle_size = write_info_to_file(fd, chunk, vad_par->chunk_size, totle_size);
		}
	}
	fd = add_wav_head(fd, hdr, totle_size);
	free(hdr);
	close(fd);
	return 1;
}

int alsa_vad(int s_rate, int f_type, int channels, int c_d_ms)
{
	int is_get_sentence = 0;
	snd_pcm_t *capture_handle;
	VAD_PARAMETER_T* vad_par = (VAD_PARAMETER_T *)malloc(sizeof(VAD_PARAMETER_T));
	
	vad_par->sample_rate = s_rate;
	vad_par->format_type = f_type;
	vad_par->num_channels = channels;
	vad_par->chunk_duration_ms = c_d_ms;
	vad_par->chunk_size = (int)(c_d_ms * s_rate / 1000);
	vad_par->chunk_bytes = vad_par->chunk_size * vad_par->format_type / 8;
	vad_par->num_window_chunks_start = 240 / vad_par->chunk_duration_ms;
	vad_par->num_window_chunks_end = vad_par->num_window_chunks_start * 5;

	vad_par->start_voice_parameter = 0.7;            //开始端点乘积因子
	vad_par->end_voice_parameter = 0.9;              //结束端点乘积因子
	vad_par->mute_time = 30000;                          //静音时间
	vad_par->voice_time = 10000;                         //语音时间	

	vad_par->TE_MIN = 100;                             //门限最小能量值
	vad_par->TE_MAX = 300;                             //门限最大能量值
	vad_par->TZ_MIN = 10;                             //门限最小过零率
	vad_par->TZ_MAX = 20;                             //门限最大过零率
	vad_par->TO_MIN = 80;                             //过零率幅度最大值
	vad_par->TO_MAX = 200;                             //过零率幅度最小值

	capture_handle = record_config_init(vad_par->sample_rate, vad_par->num_channels, vad_par->format_type, CAPTURE_DEVICE);
	
	is_get_sentence = vad(vad_par, capture_handle);
	snd_pcm_close(capture_handle);
	return is_get_sentence;
}

void main(void)
{
	alsa_vad(16000, 16, 1, 20);
}