# ph_read_mcp3008.py
# Reads DFRobot pH V2 (AO) via MCP3008 CH0 and prints pH + mV.
# - SPI: bus 0, CE0 (/dev/spidev0.0)
# - VREF = 3.3 V
# - Uses ph_cal.json if present; else defaults (rough) v7=1650 mV, v4=1800 mV.

import spidev, time, json, os

# ---------- MCP3008 setup ----------
VREF = 3.3  # volts at MCP3008 VREF (wired to Pi 3V3)

spi = spidev.SpiDev()
spi.open(0, 0)                  # bus 0, CE0; change to (0,1) if you wired CS to CE1
spi.max_speed_hz = 1350000

def read_ch0_mv():
    # Single-ended CH0 command: [1, (8+ch)<<4, 0]
    resp = spi.xfer2([1, (8 + 0) << 4, 0])
    raw  = ((resp[1] & 0x03) << 8) | resp[2]   # 0..1023
    mv   = (raw * VREF / 1023.0) * 1000.0
    return raw, mv

# ---------- Calibration handling ----------
# If ph_cal.json exists, use it. Else use rough defaults to get you going.
# Defaults assume ~1.65 V at pH 7 and ~1.80 V at pH 4 (DFRobot V2 typical).
def load_cal():
    try:
        with open("ph_cal.json") as f:
            cal = json.load(f)
            return cal["a"], cal["b"]
    except Exception:
        v7 = 1650.0  # mV at pH 7 (rough)
        v4 = 1800.0  # mV at pH 4 (rough)
        a  = (4.0 - 7.0) / (v4 - v7)   # slope (pH per mV)
        b  = 7.0 - a * v7              # intercept
        return a, b

a, b = load_cal()

def mv_to_ph(mv):
    return a * mv + b

# ---------- Main loop ----------
try:
    while True:
        raw, mv = read_ch0_mv()
        ph = mv_to_ph(mv)
        print(f"raw={raw:4d}   {mv:7.1f} mV   pH={ph:5.2f}")
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    spi.close()
