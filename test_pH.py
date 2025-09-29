# mcp3008_probe.py
import spidev, time
VREF = 3.3

def read_ch0(spi):
    resp = spi.xfer2([1, (8+0)<<4, 0])
    raw = ((resp[1]&3)<<8) | resp[2]
    mv  = (raw*VREF/1023.0)*1000
    return resp, raw, mv

for dev in [(0,0),(0,1)]:
    spi = spidev.SpiDev(); spi.open(*dev); spi.max_speed_hz=1350000
    resp, raw, mv = read_ch0(spi); spi.close()
    print(f"CE{dev[1]} resp={resp}  raw={raw:4d}  {mv:7.1f} mV")
