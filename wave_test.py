'''
    (c) 2021  Daniel Perron
    MIT License 

    example of audio output using PWM and DMA
    right now it  works only with wave file at
    8000 sample rate , stereo and 16 bits
    
    GPIO pin 14 and 15 are the output
    You need to use headphone with a 1K resistor in series on
    left and right speaker
    
    The myPWM subclass set the maximum count to 255 at a frequency around  122.5KHz.
    
    The myDMA class allow to use direct memory access to transfer each frame at the current sample rate
    
    
    You need to install the wave.py and chunk.py  from
         https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio
    
    How it works,
    
       1 - We set the PWM  to a range of 255, 1023 for 10 bits, at 122Khz
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
import utime
from myDMA import myDMA
from myPWM import myPWM
from machine import Pin



usePWM_10Bits = True

if usePWM_10Bits:
    PWM_DIVIDER = 1
    PWM_TOP = 1023
    PWM_HALF = 512
    PWM_CONVERSION = 64
else:
    # force 8 bit
    PWM_DIVIDER = 4
    PWM_TOP = 255
    PWM_HALF = 128
    PWM_CONVERSION = 256



# set  PWM to a full range of 0..255 or (0.1023) for 10 bits at 122Khz
pwm_even = myPWM(Pin(14),divider=PWM_DIVIDER,top=PWM_TOP)
# set PWM output in center 
pwm_even.duty(PWM_HALF)

pwm_odd = myPWM(Pin(15),divider=PWM_DIVIDER,top=PWM_TOP)
pwm_odd.duty(PWM_HALF)


# open Audio file and get information
audioFile='fines22.wav'

f = wave.open(audioFile,'rb')

rate = f.getframerate()
bytesDepth = f.getsampwidth() 
channels = f.getnchannels()
frameCount = f.getnframes()

print("rate",rate)
print("byte depth",bytesDepth)
print("channels",channels)
print("# of frames",frameCount)


# Set DMA channel and timer rate
# the divider set the rate at 2Khz (125Mhz//62500)
# The multiplier  use the sample rate to adjust it correctly
dma0 = myDMA(10,timer=3,clock_MUL= rate // 2000, clock_DIV=62500) 
dma1 = myDMA(11,timer=3)  # don't need to set  timer clock

# specify number of frame per chunk
nbFrame=2048

#create a byte array to hold the data for DMA
# 2 channels 16 bits

# need to alternate DMA buffer
toggle = True


# loop until is done
frameLeft = frameCount

while frameLeft>0:
    # first DMA
    if frameLeft < nbFrame:
        nbFrame = frameLeft
    nbData = nbFrame * 2
    s = f.readframes(nbFrame)
    value = struct.unpack('hh'*(nbFrame),s)
    value = [PWM_HALF + (i // PWM_CONVERSION) for i in value]

    if toggle:
        V1 = struct.pack('hh'*nbFrame,*value)
        # check if previous DMA is done    
        while dma0.isBusy():
             pass
        # Start DMA with the new audio data
        # the destination is the register address of the odd and even PWM set count
        # this is why the destination increment is false.
        dma1.move(uctypes.addressof(V1),pwm_even.PWM_CC,nbFrame*4,data_size=4,dst_inc=False)
    else:
        V0 = struct.pack('hh'*nbFrame,*value)
        # check if previous DMA is done    
        while dma1.isBusy():
             pass
        # Start DMA with the new audio data
        # the destination is the register address of the odd and even PWM set count
        # this is why the destination increment is false.
        dma0.move(uctypes.addressof(V0),pwm_even.PWM_CC,nbFrame*4,data_size=4,dst_inc=False)
    toggle = not toggle
    frameLeft -= nbFrame

f.close()    

pwm_even.duty(PWM_HALF)
pwm_odd.duty(PWM_HALF)

    