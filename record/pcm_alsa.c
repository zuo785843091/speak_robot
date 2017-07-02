#include "pcm_alsa.h"
/*
    作者: hntea_hong
    函数功能：录音初始化配置
    参数说明：
            rate:采样频率
            channle:通道数
            sample:样本长度　16/8
            dev_name:　pcm 设备
    返回值：设备回话柄
*/
snd_pcm_t* record_config_init(u32 rate,u32 channle,u8 sample,const char* dev_name)
{
    int i;
    int err;
    int dir = 0;
    snd_pcm_t* capture_handle;  
    snd_pcm_hw_params_t *hw_params;

    //以录音形式打开设备
    if((err = snd_pcm_open(&capture_handle, dev_name, SND_PCM_STREAM_CAPTURE, 0)) < 0) {
        fprintf(stderr, "cannot open audio device %s(%s)\n",\
        dev_name,snd_strerror(err));
        exit(1);
    }

    //申请硬件参数配置空间
    if((err = snd_pcm_hw_params_malloc(&hw_params)) < 0) {
        fprintf(stderr,\
        "cannot allocate hardware parameter structure(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    //填充参数空间
    if((err = snd_pcm_hw_params_any(capture_handle, hw_params)) < 0) {
        fprintf(stderr,\
         "cannot initialize hardware parameter structure(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    //配置处理模式
    if((err = snd_pcm_hw_params_set_access(capture_handle, hw_params, SND_PCM_ACCESS_RW_INTERLEAVED)) < 0) {
        fprintf(stderr, "cannot set access type(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    //配置样本值
    switch(sample)
    {
        case 8:
            if((err = snd_pcm_hw_params_set_format(capture_handle,\
             hw_params, SND_PCM_FORMAT_S8 )) < 0) {
                fprintf(stderr, "cannot set sample format(%s)\n",
                snd_strerror(err));
                exit(1);
            }   
            break;
        case 16:
            if((err = snd_pcm_hw_params_set_format(capture_handle, hw_params, SND_PCM_FORMAT_S16_LE)) < 0) {
                fprintf(stderr, "cannot set sample format(%s)\n",
                snd_strerror(err));
                exit(1);
            }
            break;
        default:
            if((err = snd_pcm_hw_params_set_format(capture_handle, hw_params, SND_PCM_FORMAT_S16_LE)) < 0) {
                fprintf(stderr, "cannot set sample format(%s)\n",
                snd_strerror(err));
                exit(1);
            }
            break;
    }

    //配置通道数
    if((err = snd_pcm_hw_params_set_channels(capture_handle, hw_params, channle)) < 0) {
        fprintf(stderr, "cannot set channel count(%s)\n",
        snd_strerror(err));
        exit(1);
    }
    
    //配置采样频率
    if((err = snd_pcm_hw_params_set_rate_near(capture_handle, hw_params, &rate, &dir)) < 0) {
        fprintf(stderr, "cannot set sample rate(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    //写入参数
    if((err = snd_pcm_hw_params(capture_handle, hw_params)) < 0) {
        fprintf(stderr, "cannot set parameters(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    //释放参数空间
    snd_pcm_hw_params_free(hw_params);

    if((err = snd_pcm_prepare(capture_handle)) < 0) {
        fprintf(stderr, "cannot prepare audio interface for use(%s)\n",
        snd_strerror(err));
        exit(1);
    }

    return capture_handle;  
}