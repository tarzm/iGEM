#!/usr/bin/env python3
"""
Bioreactor Monitoring System Backend
Handles temperature and pH sensor readings, fan control, and data logging
"""

import glob
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading
import random
from collections import deque
import os

# For Raspberry Pi GPIO (will be mocked if not available)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("RPi.GPIO not available - using mock GPIO for development")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bioreactor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MockGPIO:
    """Mock GPIO for development on non-Raspberry Pi systems"""
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0
    
    @staticmethod
    def setmode(mode): pass
    @staticmethod
    def setup(pin, mode): pass
    @staticmethod
    def output(pin, state): 
        logger.info(f"Mock GPIO: Pin {pin} set to {'HIGH' if state else 'LOW'}")
    @staticmethod
    def cleanup(): pass


class TemperatureSensor:
    """Handles DS18B20 temperature sensor readings"""
    
    def __init__(self):
        self.device_path = None
        self._find_device()
    
    def _find_device(self):
        """Find the DS18B20 device path"""
        try:
            devices = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')
            if devices:
                self.device_path = devices[0]
                logger.info(f"Temperature sensor found at: {self.device_path}")
            else:
                logger.warning("No DS18B20 temperature sensor found")
        except Exception as e:
            logger.error(f"Error finding temperature sensor: {e}")
    
    def read_celsius(self) -> Optional[float]:
        """Read temperature in Celsius"""
        if not self.device_path:
            # Return mock data for development
            return 25.0 + random.uniform(-2, 5)
        
        try:
            with open(self.device_path, 'r') as f:
                lines = f.read().strip().splitlines()
            
            # Check if reading is valid
            if lines[0].strip()[-3:] != 'YES':
                return None
            
            # Extract temperature
            temp_line = lines[1]
            temp_mdeg = int(temp_line.split('t=')[1])
            return temp_mdeg / 1000.0
            
        except Exception as e:
            logger.error(f"Error reading temperature: {e}")
            return None
    
    def read_fahrenheit(self) -> Optional[float]:
        """Read temperature in Fahrenheit"""
        celsius = self.read_celsius()
        if celsius is not None:
            return celsius * 9/5 + 32
        return None


class PHSensor:
    """Handles pH sensor readings (simulated for now)"""
    
    def __init__(self):
        self.calibration_offset = 0.0
        # Override support (e.g., on Pi without pH hardware)
        # Set PH_OVERRIDE (e.g., "7.2") to force a constant pH
        env_override = os.environ.get('PH_OVERRIDE')
        self.override_enabled = env_override is not None
        try:
            self.override_value = float(env_override) if env_override is not None else 7.2
        except Exception:
            self.override_value = 7.2
        logger.info("pH sensor initialized")
    
    def read_ph(self) -> Optional[float]:
        """Read pH value"""
        try:
            if self.override_enabled:
                return max(0, min(14, self.override_value + self.calibration_offset))
            # For development, return simulated pH values
            # In real implementation, this would read from ADC connected to pH probe
            base_ph = 7.2
            variation = random.uniform(-0.3, 0.3)
            return max(0, min(14, base_ph + variation + self.calibration_offset))
        except Exception as e:
            logger.error(f"Error reading pH: {e}")
            return None
    
    def calibrate(self, known_ph: float, measured_ph: float):
        """Calibrate pH sensor with known reference"""
        self.calibration_offset = known_ph - measured_ph
        logger.info(f"pH sensor calibrated with offset: {self.calibration_offset}")

    # Simple setters to control override at runtime
    def set_override(self, enabled: bool, value: Optional[float] = None):
        self.override_enabled = bool(enabled)
        if value is not None:
            try:
                self.override_value = float(value)
            except Exception:
                pass


class FanController:
    """Controls cooling fan based on temperature"""
    
    def __init__(self, fan_pin: int = 18, temp_threshold: float = 28.0):
        self.fan_pin = fan_pin
        self.temp_threshold = temp_threshold
        self.fan_running = False
        
        # Initialize GPIO
        if GPIO_AVAILABLE:
            self.gpio = GPIO
        else:
            self.gpio = MockGPIO
        
        self.gpio.setmode(self.gpio.BCM)
        self.gpio.setup(self.fan_pin, self.gpio.OUT)
        self.gpio.output(self.fan_pin, self.gpio.LOW)
        
        logger.info(f"Fan controller initialized on pin {fan_pin}, threshold: {temp_threshold}°C")
    
    def control_fan(self, temperature: float):
        """Control fan based on temperature"""
        if temperature > self.temp_threshold and not self.fan_running:
            self.start_fan()
        elif temperature <= self.temp_threshold - 1.0 and self.fan_running:  # Hysteresis
            self.stop_fan()
    
    def start_fan(self):
        """Start the cooling fan"""
        self.gpio.output(self.fan_pin, self.gpio.HIGH)
        self.fan_running = True
        logger.info("Cooling fan started")
    
    def stop_fan(self):
        """Stop the cooling fan"""
        self.gpio.output(self.fan_pin, self.gpio.LOW)
        self.fan_running = False
        logger.info("Cooling fan stopped")
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        self.gpio.cleanup()


class BioreactorMonitor:
    """Main bioreactor monitoring system"""
    
    def __init__(self):
        self.temp_sensor = TemperatureSensor()
        self.ph_sensor = PHSensor()
        self.fan_controller = FanController()
        
        self.current_data = {
            'temperature_c': None,
            'temperature_f': None,
            'ph': None,
            'fan_running': False,
            'timestamp': None,
            'status': 'unknown'
        }
        # In-memory history: list of dicts with timestamp (iso), ts (epoch ms), temperature_c, ph, fan_running
        self.history = deque()  # unbounded; we'll trim by time window on append
        
        self.running = False
        self.monitor_thread = None
        
        logger.info("Bioreactor monitor initialized")
    
    def get_algae_status(self, temp: float, ph: float) -> Dict[str, str]:
        """Determine algae health status based on sensor readings"""
        if temp is None or ph is None:
            return {'status': 'unknown', 'emoji': '❓', 'message': 'Sensor data unavailable'}
        
        # Optimal conditions for most algae: 20-30°C, pH 6.5-8.5
        temp_ok = 20 <= temp <= 30
        ph_ok = 6.5 <= ph <= 8.5
        
        if temp_ok and ph_ok:
            return {'status': 'excellent', 'emoji': '🌱', 'message': 'Algae are thriving!'}
        elif (18 <= temp <= 32) and (6.0 <= ph <= 9.0):
            return {'status': 'good', 'emoji': '😊', 'message': 'Algae are doing well'}
        elif (15 <= temp <= 35) and (5.5 <= ph <= 9.5):
            return {'status': 'fair', 'emoji': '😐', 'message': 'Algae are surviving'}
        else:
            return {'status': 'poor', 'emoji': '😰', 'message': 'Algae are stressed!'}
    
    def read_sensors(self):
        """Read all sensor data"""
        temp_c = self.temp_sensor.read_celsius()
        temp_f = self.temp_sensor.read_fahrenheit()
        ph = self.ph_sensor.read_ph()
        
        # Control fan based on temperature
        if temp_c is not None:
            self.fan_controller.control_fan(temp_c)
        
        # Get algae status
        algae_status = self.get_algae_status(temp_c, ph)
        
        self.current_data = {
            'temperature_c': round(temp_c, 2) if temp_c else None,
            'temperature_f': round(temp_f, 2) if temp_f else None,
            'ph': round(ph, 2) if ph else None,
            'fan_running': self.fan_controller.fan_running,
            'timestamp': datetime.now().isoformat(),
            'algae_status': algae_status
        }
        # Append to in-memory history and trim to a reasonable window (e.g., 24h)
        try:
            now_dt = datetime.now()
            entry = {
                'ts': int(now_dt.timestamp() * 1000),
                'timestamp': self.current_data['timestamp'],
                'temperature_c': self.current_data['temperature_c'],
                'ph': self.current_data['ph'],
                'fan_running': self.current_data['fan_running'],
            }
            self.history.append(entry)
            # Trim anything older than 24 hours to bound memory usage
            cutoff = now_dt - timedelta(hours=24)
            cutoff_ms = int(cutoff.timestamp() * 1000)
            while self.history and self.history[0]['ts'] < cutoff_ms:
                self.history.popleft()
        except Exception as e:
            logger.debug(f"History append/trim error: {e}")

        return self.current_data
    
    def start_monitoring(self, interval: float = 2.0):
        """Start continuous monitoring"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    data = self.read_sensors()
                    logger.info(f"T: {data['temperature_c']}°C, pH: {data['ph']}, "
                              f"Fan: {data['fan_running']}, Status: {data['algae_status']['message']}")
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.fan_controller.cleanup()
        logger.info("Monitoring stopped")
    
    def get_current_data(self) -> Dict:
        """Get current sensor data"""
        return self.current_data.copy()

    def get_history(self, minutes: int = 30):
        """Return history entries within the last `minutes` minutes as a list of dicts"""
        try:
            minutes = max(1, min(int(minutes), 24 * 60))  # clamp 1..1440
        except Exception:
            minutes = 30
        now_ms = int(datetime.now().timestamp() * 1000)
        cutoff_ms = now_ms - minutes * 60 * 1000
        return [e for e in list(self.history) if e['ts'] >= cutoff_ms]


if __name__ == "__main__":
    # Test the bioreactor monitor
    monitor = BioreactorMonitor()
    
    try:
        monitor.start_monitoring(interval=1.0)
        
        # Run for a demo period
        for i in range(30):
            data = monitor.get_current_data()
            print(f"\n--- Reading {i+1} ---")
            print(f"Temperature: {data['temperature_c']}°C ({data['temperature_f']}°F)")
            print(f"pH: {data['ph']}")
            print(f"Fan Running: {data['fan_running']}")
            print(f"Algae Status: {data['algae_status']['emoji']} {data['algae_status']['message']}")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        monitor.stop_monitoring()
