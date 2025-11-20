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
