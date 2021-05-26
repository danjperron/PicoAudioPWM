'''
    (c) 2021  Daniel Perron
    MIT License

    example of audio output using PWM and DMA
    right now it  works only with wave file at
    8000 sample rate , stereo or mono, and 16 bits audio

    GPIO  2 & 3  pin 4 and 5 are the output
    You need to use headphones with a 1K resistor in series on
    left and right speaker

    The myPWM subclass set the maximum count to 255 at a frequency around  122.5KHz.

    The myDMA class allow to use direct memory access to transfer each frame at the current sample rate


    You need to install the wave.py and chunk.py  from
         https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio
         
    SDCard.py  is available in  https://github.com/micropython/micropython/tree/master/drivers/sdcard
      please be sure to rename it SDCard.py into the pico lib folder
    

    ***  be sure to increase the SPI clock speed > 5MHz
    *** once SDCard is initialize set the spi to an higher clock


    How it works,

       1 - We set the PWM  to a range of 255, 1023 for 10 bits, at 122Khz
       2 - We read the wave file using the class wave which will set the sample rate and read the audio data by chunk
       3 - Mono files are converted to stereo by duplicating the original audio samples
       4 - Each chunk are converted to  16 bit signed to  unsigned char with the middle at 128
       5 - Wait for the DMA to be completed.  On first it will be anyway.
       6 - The converted chunk is then pass to the DMA to be transfer at the sample rate using one of build-in timer
       7 - Go on step 2 until is done.

    P.S. use rshell to transfer wave files to the Pico file system

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
#
#---USES 
import os as uos
from wavePlayer import wavePlayer


if __name__ == "__main__":

    player = wavePlayer()
    waveFolder= "/flash"
    wavelist = []

    for i in uos.listdir(waveFolder):
        if i.find(".wav")>=0:
            wavelist.append(waveFolder+"/"+i)
        elif i.find(".WAV")>=0:
            wavelist.append(waveFolder+"/"+i)
            
    if not wavelist :
        print("Warning NO '.wav' files")
    else:
        print("Will play these '.wav' files","/n",wavelist)
        try:
            while True:
                for  i in wavelist:
                    print(i)
                    player.play(i)
        except KeyboardInterrupt:
            player.stop()
    print("wavePlayer terminated")

