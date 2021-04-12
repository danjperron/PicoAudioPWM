from machine import mem32
import uctypes


class myDMA:
    
    def __init__(self, channel,timer=None, clock_MUL=None, clock_DIV=None):
        self.channel = channel
        self.timer = timer
        self.DMA_BASE = 0x50000000
        self.DMA_CH_BASE = self.DMA_BASE + (0x40 * channel)
        self.READ_ADDR = self.DMA_CH_BASE + 0
        self.WRITE_ADDR = self.DMA_CH_BASE + 4 
        self.TRANS_COUNT = self.DMA_CH_BASE + 8
        self.CTRL_TRIG = self.DMA_CH_BASE + 12
        self.MULTI_TRIG = self.DMA_BASE + 0x430
        self.CHAIN_ABORT = self.DMA_BASE + 0x444
        self.ALIAS_CTRL  = self.DMA_CH_BASE + 12
        self.timer_channel = timer
        self.clock_MUL= clock_MUL
        self.clock_DIV = clock_DIV

        if self.timer_channel is None:
            self.TIMER = None
        else:
            self.TIMER = self.DMA_BASE + 0x420 + ( 4 * self.timer_channel)
            if not( self.clock_DIV is None  or self.clock_MUL is None):
                mem32[self.TIMER]= self.clock_MUL << 16 | self.clock_DIV
        
        mem32[self.CTRL_TRIG] = 0
        mem32[self.CHAIN_ABORT] = 1 << self.channel 

    def enable(self):
        mem32[self.CTRL_TRIG | 0x2000]= 1

    def pause(self):
        mem32[self.CTRL_TRIG | 0x3000]= 1
        
        
     
     
    def setCtrl(self, src_inc=True, dst_inc=True,data_size=1):
        self.data_size=data_size
        DATA_SIZE = 0
        if data_size == 2:
           DATA_SIZE = 1
        elif data_size == 4:
           DATA_SIZE = 2
        ctrl = 0
        ctrl += (DATA_SIZE << 2)
        
        if self.timer_channel is None:
            ctrl += (0x3f << 15)
        else:
            ctrl += ((0x3b + self.timer_channel) << 15)
        # chain to
        ctrl += (self.channel << 11)
        if src_inc:
            ctrl += 0x10
        if dst_inc:
            ctrl += 0x20
        self.ctrl = ctrl
        
     
    def move(self, src_add, dst_add,count,enable=True):
        #        mem32[self.CTRL_TRIG] = 0
        #        mem32[self.CHAIN_ABORT] = 1 << self.channel 
        mem32[self.WRITE_ADDR] = dst_add
        mem32[self.READ_ADDR] =  src_add
        mem32[self.TRANS_COUNT] = count // self.data_size
        #/if enable:
        mem32[self.CTRL_TRIG] = self.ctrl
        #else:
        #         mem32[self.CTRL_TRIG] = self.ctrl & 0xfffffffe
        
    def isBusy(self):
            flag = mem32[self.CTRL_TRIG]
            if (flag & 0x80000000) !=  0:
                return False
            if (flag & ( 1<<24)) == 0:
                return False
            return True
            
if __name__ == "__main__":
    import urandom, time
    tSize = 96
    src = bytearray(tSize)
    dst = bytearray(tSize)

    for i in range(tSize):
        src[i]= urandom.randint(0,255)
 
   # initialize DMA channel 11 , use timer 3 and set clock to 125MHz/15625 = 8000Hz
    dma = myDMA(11,timer=3,clock_MUL=1, clock_DIV=15625)
    start = time.ticks_us()
    dma.move(uctypes.addressof(src),uctypes.addressof(dst),tSize)
    end = time.ticks_us() 

    print("src= ",src)
    print("\ndst= ",dst)

    length_us = end - start
    if length_us > 0:
        print("\ntook {} us  rate = {} bytes /sec\n".format(length_us,1_000_000.0 * tSize / length_us))     