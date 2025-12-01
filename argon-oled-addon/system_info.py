"""
System information retrieval module
Provides methods to get system metrics like CPU, RAM, storage, temperature, etc.
"""

import os


class SystemInfo:
    """Handles system information gathering"""
    
    def __init__(self, temp_unit='C'):
        self.temp_unit = temp_unit
        self.prev_idle = None
        self.prev_total = None
    
    def get_cpu_temp(self):
        """Get CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_c = float(f.read()) / 1000.0
                if self.temp_unit == 'F':
                    return (temp_c * 9/5) + 32
                return temp_c
        except:
            return 0
    
    def get_cpu_usage(self):
        """Get CPU usage percentage"""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                fields = line.split()
                idle = float(fields[4])
                total = sum(float(x) for x in fields[1:])
                
                if self.prev_idle is None:
                    self.prev_idle = idle
                    self.prev_total = total
                    return 0
                
                diff_idle = idle - self.prev_idle
                diff_total = total - self.prev_total
                self.prev_idle = idle
                self.prev_total = total
                
                if diff_total == 0:
                    return 0
                
                usage = 100 * (1 - diff_idle / diff_total)
                return max(0, min(100, usage))
        except:
            return 0
    
    def get_memory_usage(self):
        """Get memory usage in MB and percentage"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                mem_total = 0
                mem_available = 0
                
                for line in lines:
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1]) / 1024  # Convert to MB
                    elif line.startswith('MemAvailable:'):
                        mem_available = int(line.split()[1]) / 1024
                
                if mem_total > 0:
                    mem_used = mem_total - mem_available
                    mem_percent = (mem_used / mem_total) * 100
                    return mem_used, mem_total, mem_percent
        except:
            pass
        return 0, 0, 0
    
    def get_disk_usage(self):
        """Get disk usage for root filesystem"""
        try:
            stat = os.statvfs('/')
            total = (stat.f_blocks * stat.f_frsize) / (1024**3)  # GB
            free = (stat.f_bavail * stat.f_frsize) / (1024**3)
            used = total - free
            percent = (used / total) * 100 if total > 0 else 0
            return used, total, percent
        except:
            return 0, 0, 0
    
    def get_fan_speed(self):
        """Get fan speed from Raspberry Pi 5 native fan connector
        Returns: dict with 'rpm' (int or None), 'pwm_percent' (int 0-100), 'status' (str)
        """
        import glob
        
        result = {
            'rpm': None,
            'pwm_percent': 0,
            'status': 'Not Found'
        }
        
        try:
            # Find hwmon devices
            hwmon_paths = glob.glob('/sys/class/hwmon/hwmon*/name')
            
            for name_file in hwmon_paths:
                try:
                    with open(name_file, 'r') as f:
                        device_name = f.read().strip()
                    
                    # Look for fan/cooling device (rp1_fan, pwm-fan, cooling_fan, etc.)
                    if any(keyword in device_name.lower() for keyword in ['fan', 'cooling', 'rp1']):
                        hwmon_dir = os.path.dirname(name_file)
                        
                        # Try to read RPM (requires tachometer connection)
                        fan_input = os.path.join(hwmon_dir, 'fan1_input')
                        if os.path.exists(fan_input):
                            with open(fan_input, 'r') as f:
                                result['rpm'] = int(f.read().strip())
                        
                        # Read PWM duty cycle (0-255 scale)
                        pwm_file = os.path.join(hwmon_dir, 'pwm1')
                        if os.path.exists(pwm_file):
                            with open(pwm_file, 'r') as f:
                                pwm_value = int(f.read().strip())
                                result['pwm_percent'] = int((pwm_value / 255) * 100)
                                
                                # Determine status
                                if result['pwm_percent'] == 0:
                                    result['status'] = 'Off'
                                elif result['rpm'] is not None:
                                    result['status'] = f"{result['rpm']} RPM"
                                else:
                                    result['status'] = f"{result['pwm_percent']}%"
                                
                                return result
                except:
                    continue
        except:
            pass
        
        return result
