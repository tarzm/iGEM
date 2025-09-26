import glob, time

def read_celsius():
    dev = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')[0]
    with open(dev) as f:
        lines = f.read().strip().splitlines()
    # lines[1] like: "t=23125"  ->  23.125 °C
    t_mdeg = int(lines[1].split('t=')[1])
    return t_mdeg / 1000.0

while True:
    print(f"{read_celsius():.3f} °C")
    time.sleep(1)


