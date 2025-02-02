# PicoAudioPWM
PWM audio on pico with 8KHz up to 44.1KHz stereo wave file
example of audio output using PWM 10 bits and DMA
The wave file needs to be stereo and 16 bits.

GPIO pin 14 and 15 are the output
you need to use head phone with a 1K resistor in series on
left and right speaker

The myPWM subclass set the maximum count to 255(8 bits)  or 1023(10bits)  at a frequency 
around 122.5KHz.

**the PWM is now on 10 bits (0..1023)

The myDMA class allows to use direct memory access to transfer each frame at the current sample rate


You need to install the wave.py and chunk.py from
     https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio

Don't forget to increase the SPI clock up to 3Mhz in order to get SD card work properly.
```
from machine import SPI,Pin
sd = SDCard.SDCard(SPI(1),Pin(13))
sd.init_spi(50_000_000)
```
See example in [wavePlayer.py](wavePlayer.py#L285)


## How it works,

   1 - We set the PWM to a range of 255 at 122Khz
   2 - We read the wave file using the class wave which will set the 
       sample rate and read the audio data by chunk
   3 - Each chunk are converted to 16 bit signed to unsigned char 
       with the middle at 128, (512 for 10 bits)
   4 - Wait for the DMA to be completed.  On first it will be 
       anyway.
   5 - The converted chunk is then pass to the DMA to be transfer at 
       the sample rate using one of build in timer
   6 - Go on step 2 until is done.
   
P.S. to transfer wave file use rshell.

## Schematics
```
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
```
**For amplifier don't use PIO4 and the capacitor should be 2200pF and connected to GND**, this should drain high frequency noise to the ground.
This formula cam be used to determine capacitance for desired frequency cut off `C = 1/(2*π*R*f)`, with 2K and 2200pF the cutoff frequency would be 36171Hz, results may vary depending on actual components selection.

## youtube example
https://www.youtube.com/watch?v=dgIQz5uy2vA
