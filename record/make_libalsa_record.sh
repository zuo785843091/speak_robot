gcc -o libalsa_record.so -shared -fPIC pcm_alsa.c alsa_record.c -lasound -ldl -lm
gcc -o libalsa_record.o pcm_alsa.c alsa_record.c -lasound -ldl -lm