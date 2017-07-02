#ifndef PCM_ALSA_H
#define PCM_ALSA_H

#include <alsa/asoundlib.h>
//#include "ros/ros.h"

#define CAPTURE_DEVICE "plughw:1,0"
#define PLAYBACK_DEVICE "default"
typedef unsigned int u32;
typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
typedef unsigned char u8;

//录音配置
extern snd_pcm_t* record_config_init(u32 rate,u32 channle,u8 sample,const char* dev_name);
//播放配置
extern snd_pcm_t* playback_config_init(u32 rate,u32 channle,u8 sample,const char* dev_name);

#endif