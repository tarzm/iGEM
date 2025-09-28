from gpiozero import OutputDevice
from time import sleep
import time, glob

fan = OutputDevice(12, active_high=True, initial_value=False)  # BCM12 (pin 32)

def read_c():
    dev = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')[0]
    with open(dev) as f:
        data = f.read()
    t_mdeg = int(data.split('t=')[1])
    return t_mdeg / 1000.0


while True:
    temp = read_c()
    print(f"{temp:.1f} °C")
    if temp > 24:
        if not fan.is_active:
            fan.on()
            print("Fan turned ON")
    else:
        if fan.is_active:
            fan.off()
            print("Fan turned OFF")
    sleep(3)
'''
    fan.off()
    print("fan is OFF")
    print(f"{read_c():.1f} °C")
    sleep(3)
    fan.on()
    print("fan is ON")
    sleep(3)
    '''

'''

try:
    while True:
        fan.on()
        print("fan is ON")
        sleep(10)

        fan.off()
        print("fan is OFF")
        sleep(10)
except KeyboardInterrupt:
    pass
finally:
    fan.off()

'''




# file: read_ds18b20.py


'''
while True:
    print(f"{read_c():.3f} °C")
    time.sleep(2)
'''
