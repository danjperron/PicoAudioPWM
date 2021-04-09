'''
    (c) 2021  Daniel Perron
    MIT License 

    example of audio output using PWM and DMA
    right now it  works only with wave file at
    8000 sample rate , stereo and 16 bits
    
    GPIO pin 14 and 15 are the output
    you need to use head phone with a 1K resistor in series on
    left and right speaker
    
    The myPWM subclass set the maximum count to 255 at a frequency around  122.5KHz.
    
    The myDMA class allow to use direct memory access to transfer each frame at the current sample rate
    
    
    You need to install the wave.py and chunk.py  from
         https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio
    
    How it works,
    
       1 - We set the PWM  to a range of 255 at 122Khz
       2 - We read the wave file using the class wave which will set the sample rate and read the audio data by chunk
       3 - Each chunk are converted to  16 bit signed to  unsigned char with the middle at 128
       4 - Wait for the DMA to be completed.  On first it will be anyway.
       4 - The converted chunk is then pass to the DMA to be transfer at the sample rate using one of build in timer
       6 - Go on step 2 until is done.
       
    P.S. to transfer wave file  use rshell.
'''
import wave
import uctypes
import struct
import array
from myDMA import myDMA
from myPWM import myPWM
from machine import Pin

# set  PWM to a full range of 0..255 at 122Khz
pwm_even = myPWM(Pin(14),divider=4,top=255)
pwm_odd = myPWM(Pin(15),divider=4,top=255)

# set PWM output in center 
pwm_even.duty(128)
pwm_odd.duty(128)


# open Audio file and get information
audioFile='fines.wav'

f = wave.open(audioFile,'rb')

rate = f.getframerate()
bytes = f.getsampwidth() 
channels = f.getnchannels()
frameCount = f.getnframes()


# Set DMA channel and timer rate
# the divider set the rate at 2Khz (125Mhz//62500)
# The multiplier  use the sample rate to adjust it correctly
dma = myDMA(11,timer=3,clock_MUL= rate // 2000, clock_DIV=62500) 


# specify number of frame per chunk
nbFrame=1024

#create a byte array to hold the data for DMA
# 2 channels 16 bits
# the LSB hold the audio value
# the MSB is always zero  since it is for the PWM

audioFrames = bytearray(4 * nbFrame)

# loop until is done
frameLeft = frameCount
while frameLeft>0:
    if frameLeft < nbFrame:
        nbFrame = frameLeft
    s = f.readframes(nbFrame)
    audioIdx=0
    for i in range(nbFrame):
        idx = i * 4
        value = struct.unpack("<hh",s[idx:idx+4])
        audioFrames[audioIdx] = 128 + (value[0] // 256)
        audioFrames[audioIdx+2] = 128 + (value[1] // 256)
        audioIdx+=4
        
    # check is previous DMA is done    
    while dma.isBusy():
         pass
    # Start DMA with the new audio data
    # the destination is the register address of the odd and even PWM set count
    # this is why the destination increment is false.
    dma.move(uctypes.addressof(audioFrames),pwm_even.PWM_CC,audioIdx,data_size=4,dst_inc=False)
    frameLeft -= nbFrame

f.close()    

pwm_even.duty(128)
pwm_odd.duty(128)
    