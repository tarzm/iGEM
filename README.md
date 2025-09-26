# Bioreactor Monitor (Raspberry Pi)

A simple Raspberry Pi-based bioreactor monitoring app that reads temperature and pH, controls a cooling fan, and provides a friendly web UI with emoji status.

## Features

- Live readings: temperature (°C/°F) and pH
- Auto fan control with adjustable temperature threshold and manual override
- Web UI with large numbers, color-coded cards, and algae mood emoji
- Works on Raspberry Pi (uses GPIO) and on laptops (uses mock sensors)

## Hardware assumptions

- Temperature sensor: DS18B20 (1-Wire)
- pH sensor: Any pH probe connected via ADC (currently simulated)
- Fan: driven via a transistor/relay on a GPIO pin (default BCM 18)

## Raspberry Pi setup

1. Enable 1-Wire for DS18B20
   - `sudo raspi-config` → Interface Options → 1-Wire → Enable
   - Reboot: `sudo reboot`

2. Check the sensor path
   - After reboot, you should see something like `/sys/bus/w1/devices/28-xxxx/w1_slave`

3. Set up Python environment
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

> Note: We purposely do not pin `RPi.GPIO` in requirements to keep cross-platform installs simple. On Pi, it is typically preinstalled. The backend falls back to a mock if `RPi.GPIO` is not available.

## Run the app

```bash
export FLASK_APP=app.py
python app.py
```

Then open http://<your-pi-ip>:5000 in a browser on your network.

## Project structure

- `bioreactor_backend.py` — Sensors, fan control, and monitoring loop
- `app.py` — Flask server, API, and HTML template serving
- `templates/index.html` — UI page
- `static/css/styles.css` — Styling
- `static/js/app.js` — Frontend logic

## Customization

- Change fan pin or temperature threshold in `FanController` (in `bioreactor_backend.py`).
- Adjust status heuristics and emoji in `BioreactorMonitor.get_algae_status()`.

## Troubleshooting

- If temperature shows `--`, verify the DS18B20 is detected and that 1-Wire is enabled.
- On non-Pi development machines, the app uses mock sensor data.
- Logs are written to `bioreactor.log`.
