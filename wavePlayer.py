'''
    (c) 2021  Daniel Perron
    MIT License

    example of audio output using PWM and DMA
    right now it  works only with wave file at
    8000 sample rate , stereo or mono, and 16 bits audio

    GPIO  2 & 3  pin 4 and 5 are the output
    You need to use headphones with a 1K resistor in series on
    left and right speaker

    The myPWM subclass sets the maximum count to 255 at a frequency around  122.5KHz.

    The myDMA class allows to use direct memory access to transfer each frame at the current sample rate


    You need to install the wave.py and chunk.py  from
         https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio
         
    SDCard.py  is available in  https://github.com/micropython/micropython/tree/master/drivers/sdcard
      please be sure to rename it SDCard.py into the pico lib folder
    

    ***  be sure to increase the SPI clock speed > 5MHz
    ***  once SDCard is initialize set the spi to an higher clock


    How it works,

       1 - We set the PWM  to a range of 255, 1023 for 10 bits, at 122Khz
       2 - We read the wave file using the class wave which will set the sample rate and read the audio data by chunk
       3 - Mono files are converted to stereo by duplicating the original audio samples
       4 - Each chunk are converted to  16 bit signed to unsigned char with the middle at 128
       5 - Wait for the DMA to be completed.  On first it will be anyway.
       6 - The converted chunk is then passed to the DMA to be transfered at the sample rate using one of built-in timer
       7 - Go on step 2 until is done.

    P.S. use rshell to transfer wave files to the Pico file system

    April 20
    Version 0.1
    ---  Add DMA chainning. This removes the glitch betweem DMA transfer
    ---  assembly function convert2PWM replace  the struct pack and compack
        since it is not necessary to convert the binary string it is way faster.
    Version 0.2
    ---  Add mono audio file handling

    For Headphones

    
             2K
    PIO2   -/\/\/-----+-----    headphone left
                      |
                     === 0.1uF
                      |
    PIO4   -----------+-----    headphone ground
                      |
                     === 0.1uF
              2k      |
    PIO3   -/\/\/-----+-----    headphone right



    For amplifier don't use PIO4 and the capacitor should be 2200pF and connected to GND. 
    
       


'''
import wave
import uctypes
from myDMA import myDMA
from myPWM import myPWM
from machine import Pin



#r0 buffer address
#r1 number of word to do
#r2 8 or 10 bit PWM
#then r2 hold data reference by r0
#r3 = 32768 to convert (-32768..32767) to (0..65535)
#r4 hold 255 or 1023 (8 or 10 bits)
#r5  hold /64  or /256 ( 6 or 8 bit shift)
@micropython.asm_thumb
def convert2PWM(r0,r1,r2):
    #r3=32768
    mov(r3,1)
    mov(r4,15)
    lsl(r3,r4)
    # 8bits or 10 bit PWM
    mov(r4,255)
    cmp(r2,10)
    bne(PWM8BITS)
    #ok we are 10 bits
    # set r4 for 1023
    lsl(r4,r4,2)
    add(r4,r4,3)
    mov(r5,6)
    b(loop)
    label(PWM8BITS)
    #ok then this is 8 bits
    #r4 already to 255
    mov(r5,8)
    label(loop)
    # get 16 bit data
    ldrh(r2,[r0,0])
    # add 32768
    add(r2,r2,r3)
    # shift right 6 bit or 8 bit
    lsr(r2,r5)
    # and 255 or 1023
    and_(r2,r4)
    # store new data
    strh(r2,[r0,0])
    add(r0,2)
    sub(r1,1)
    bgt(loop)

pass
@micropython.asm_thumb
def interleavebytes(r0,r1,r2):
#r0 MONO wav audio buffer address
#r1 Stereo wav audio ouput buffer address
#r2 number of halfwords (16 bit audio samples) from MONO buffer to convert

    label(loop)
    # get 16 bit data
    ldrh(r3,[r0,0])
    # copy over
    strh(r3,[r1,0])
    add(r1,2)
    # and duplicate for second channel
    strh(r3,[r1,0])
    # point to next audio data halfword
    add(r1,2)
    add(r0,2)
    # decrement counter and loop unless zero
    sub(r2,1)
    bgt(loop)


class wavePlayer:
    def __init__(self,leftPin=Pin(2),rightPin=Pin(3), virtualGndPin=Pin(4),
                 dma0Channel=10,dma1Channel=11,dmaTimer=3,pwmBits=10):
        #left channel Pin needs to be an even GPIO Pin number
        #right channel Pin needs to be left channel + 1
        self.pwmBits=pwmBits
        self.PWM_DIVIDER = 1
        if self.pwmBits == 10:
            self.PWM_TOP = 1023
            self.PWM_HALF = 512
        else:
            # 8 bits
            self.PWM_TOP = 255
            self.PWM_HALF = 128

        self.leftPin=leftPin
        self.rightPin=rightPin
        self.virtualGndPin=virtualGndPin

        # set PWM
        self.leftPWM=myPWM(leftPin,divider=self.PWM_DIVIDER,top=self.PWM_TOP)
        self.leftPWM.duty(self.PWM_HALF)
        self.rightPWM=myPWM(rightPin,divider=self.PWM_DIVIDER,top=self.PWM_TOP)
        self.rightPWM.duty(self.PWM_HALF)
        if not (self.virtualGndPin is None):
            self.virtualGndPWM=myPWM(self.virtualGndPin,divider=self.PWM_DIVIDER,top=self.PWM_TOP)
            self.virtualGndPWM.duty(self.PWM_HALF)


        # set DMA channel
        self.dma0Channel = dma0Channel
        self.dma1Channel = dma1Channel
        self.dmaTimer = dmaTimer


    def stop(self):
        self.dma0.abort()
        self.dma1.abort()

    def play(self,filename):
        # open Audio file and get information

        f = wave.open(filename,'rb')

        rate = f.getframerate()
        bytesDepth = f.getsampwidth()
        channels = f.getnchannels()
        frameCount = f.getnframes()

        # set number of Frames/chunk and DMAunitSize for Stereo samples
        DMAunitSize = 4
        nbFrame = 2048
        # adjust down if 1 channel (mono)
        if channels == 1:
            nbFrame=1024
        #number of 16bit audio chunks per Frame
        nbData = nbFrame*2
        # Set DMA channel and timer rate
        # the divider set the rate at 2Khz (125Mhz//62500)
        # The multiplier  use the sample rate to adjust it correctly
        if rate == 44100:
            self.dma0 = myDMA(self.dma0Channel,timer=self.dmaTimer,clock_MUL= 15, clock_DIV=42517)
        else:
            self.dma0 = myDMA(self.dma0Channel,timer=self.dmaTimer,clock_MUL= rate // 2000, clock_DIV=62500)
        self.dma1 = myDMA(self.dma1Channel,timer=self.dmaTimer)  # don't need to set  timer clock

        #setup DMA   chain dma0 to dma1 and vice versa
        self.dma0.setCtrl(src_inc=True, dst_inc=False,data_size=DMAunitSize,chainTo=self.dma1.channel)
        self.dma1.setCtrl(src_inc=True, dst_inc=False,data_size=DMAunitSize,chainTo=self.dma0.channel)

        # need to alternate DMA buffer using a toggle flag
        toggle = True
        # need to start first frame
        First = True
        # loop until is done
        frameLeft = frameCount

        while frameLeft>0:
         # first DMA
            if frameLeft < nbFrame:
                nbFrame = frameLeft
                nbData = nbFrame*2
            if toggle:
                t1 = f.readframes(nbFrame)
#--- Duplicate mono audio samples to simulate stereo sound (on both channels)
                if channels ==1:
                    t3 = bytearray(4096)
                    interleavebytes(uctypes.addressof(t1),uctypes.addressof(t3),nbFrame)
                    t1=t3
#--- make t1 stereo data to PWM compatible
                convert2PWM(uctypes.addressof(t1), nbData,self.pwmBits)
                self.dma1.move(uctypes.addressof(t1),self.leftPWM.PWM_CC,nbFrame*DMAunitSize)
                # check if previous DMA is done
                while self.dma0.isBusy():
                     pass
                # start DMA.
                # Since they are chained we need to start the first DMA
                if First:
                  self.dma1.start()
                  First = False
            else:
                t0 = f.readframes(nbFrame)
#--- Duplicate mono audio samples to simulate stereo sound (on both channels)
                if channels == 1:
                    t3 = bytearray(4096)
                    interleavebytes(uctypes.addressof(t0),uctypes.addressof(t3),nbFrame)
                    t0=t3
#--- make t0 stereo data to PWM compatible
                convert2PWM(uctypes.addressof(t0), nbData,self.pwmBits)
                self.dma0.move(uctypes.addressof(t0),self.leftPWM.PWM_CC,nbFrame*DMAunitSize)
                # check if previous DMA is done
                while self.dma1.isBusy():
                     pass
            toggle = not toggle
            frameLeft -= nbFrame

        if toggle:
            self.dma1.pause()
            while self.dma0.isBusy():
                pass
            self.dma0.pause()
        else:
            self.dma0.pause()
            while self.dma1.isBusy():
                pass
            self.dma1.pause()
        f.close()
        self.stop()


if __name__ == "__main__":

    import uos
    import SDCard

    # mount SDCard
    from machine import SPI,Pin
    sd = SDCard.SDCard(SPI(1),Pin(13))

    #need to pump up the SPI clock rate
    # below 3MHz it won't work!
    sd.init_spi(50_000_000)
    uos.mount(sd,"/sd")

    player = wavePlayer()

    waveFolder= "/sd/Wendy"
    wavelist = []

    for i in uos.listdir(waveFolder):
        if i.find(".wav")>=0:
            wavelist.append(waveFolder+"/"+i)
        elif i.find(".WAV")>=0:
            wavelist.append(waveFolder+"/"+i)
            

    try:
        for  i in wavelist:
            print(i)
            player.play(i)
    except KeyboardInterrupt:
        player.stop()
