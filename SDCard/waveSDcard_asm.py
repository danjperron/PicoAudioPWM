'''
    (c) 2021  Daniel Perron
    MIT License 

    example of audio output using PWM and DMA
    right now it  works only with wave file at
    8000 sample rate , stereo and 16 bits
    
    GPIO  2 & 3  pin 4 and 5 are the output
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
import uos
import SDCard
from myDMA import myDMA
from myPWM import myPWM
from machine import Pin


# mount SDCard
from machine import SPI,Pin
sd = SDCard.SDCard(SPI(1),Pin(13))
uos.mount(sd,"/sd")




# force 8 bit
PWM_DIVIDER = 2
PWM_TOP = 255
PWM_HALF = 128
PWM_CONVERSION = 256

#r0 buffer address
#r1 number of word to do    
#r2 hold data reference by r0
#r3 = 32768 to convert (-32768..32767) to (0..65535)
#r4 scratch pad
@micropython.asm_thumb
def convert2PWM(r0,r1):
    #r3=32768
    mov(r3,1)
    mov(r4,15)
    lsl(r3,r4)
    label(loop)
    # get 16 bit data
    ldrh(r2,[r0,0])
    # add 32768
    add(r2,r2,r3)
    # shift right 8 bit
    mov(r4,8)
    asr(r2,r4)
    # and 255
    mov(r4,255)
    and_(r2,r4)
    # store new data
    strh(r2,[r0,0])
    add(r0,2)
    sub(r1,1)
    bgt(loop)
    
    
# set  PWM to a full range of 0..255 or (0.1023) for 10 bits at 122Khz
pwm_even = myPWM(Pin(2),divider=PWM_DIVIDER,top=PWM_TOP)
# set PWM output in center 
pwm_even.duty(PWM_HALF)

pwm_odd = myPWM(Pin(3),divider=PWM_DIVIDER,top=PWM_TOP)
pwm_odd.duty(PWM_HALF)


# open Audio file and get information
audioFile='/sd/Luke44.wav'

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
if rate == 44100:
    dma0 = myDMA(10,timer=3,clock_MUL= 15, clock_DIV=42517)
else:
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
#setup DMA
dma0.setCtrl(src_inc=True, dst_inc=False,data_size=4)
dma1.setCtrl(src_inc=True, dst_inc=False,data_size=4)

while frameLeft>0:
    # first DMA
    if frameLeft < nbFrame:
        nbFrame = frameLeft
    nbData = nbFrame * 2

    if toggle:
        t1 = f.readframes(nbFrame)
        convert2PWM(uctypes.addressof(t1), nbData)
        dma1.move(uctypes.addressof(t1),pwm_even.PWM_CC,nbFrame*4)
        # check if previous DMA is done    
        while dma0.isBusy():
             pass
        # start DMA
        dma1.enable()
    else:
        t0 = f.readframes(nbFrame)
        convert2PWM(uctypes.addressof(t0), nbData)
        dma0.move(uctypes.addressof(t0),pwm_even.PWM_CC,nbFrame*4)
        # check if previous DMA is done    
        while dma1.isBusy():
             pass
        dma0.enable()
    toggle = not toggle
    frameLeft -= nbFrame

f.close()    

pwm_even.duty(PWM_HALF)
pwm_odd.duty(PWM_HALF)

    