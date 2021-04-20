# PicoAudioPWM
PWM audio on pico with 8KHz up to 22KHz stereo wave file
    example of audio output using PWM and DMA
    right now it works only with wave file at
    8000 and up to 22000 sample rate , stereo and 16 bits
    
    GPIO pin 14 and 15 are the output
    you need to use head phone with a 1K resistor in series on
    left and right speaker
    
    The myPWM subclass set the maximum count to 255 at a frequency 
around 122.5KHz.
    
    ** the PWM is now on 10 bits (0..1023)
    
    The myDMA class allows to use direct memory access to transfer each 
frame at the current sample rate
    
    
    You need to install the wave.py and chunk.py from
         https://github.com/joeky888/awesome-micropython-lib/tree/master/Audio
    
    How it works,
    
       1 - We set the PWM to a range of 255 at 122Khz
       2 - We read the wave file using the class wave which will set the 
sample rate and read the audio data by chunk
       3 - Each chunk are converted to 16 bit signed to unsigned char 
with the middle at 128, (512 for 10 bits)
       4 - Wait for the DMA to be completed.  On first it will be 
anyway.
       4 - The converted chunk is then pass to the DMA to be transfer at 
the sample rate using one of build in timer
       6 - Go on step 2 until is done.
       
    P.S. to transfer wave file use rshell.
