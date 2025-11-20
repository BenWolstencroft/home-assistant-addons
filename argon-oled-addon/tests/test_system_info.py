"""
Unit tests for system_info module
"""

import os
import unittest
from unittest.mock import patch, mock_open
from system_info import SystemInfo


class TestSystemInfo(unittest.TestCase):
    """Test SystemInfo class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.system_info_c = SystemInfo(temp_unit='C')
        self.system_info_f = SystemInfo(temp_unit='F')
    
    def test_init(self):
        """Test SystemInfo initialization"""
        self.assertEqual(self.system_info_c.temp_unit, 'C')
        self.assertEqual(self.system_info_f.temp_unit, 'F')
        self.assertIsNone(self.system_info_c.prev_idle)
        self.assertIsNone(self.system_info_c.prev_total)
    
    @patch('builtins.open', mock_open(read_data='45000'))
    def test_get_cpu_temp_celsius(self):
        """Test CPU temperature in Celsius"""
        temp = self.system_info_c.get_cpu_temp()
        self.assertEqual(temp, 45.0)
    
    @patch('builtins.open', mock_open(read_data='45000'))
    def test_get_cpu_temp_fahrenheit(self):
        """Test CPU temperature in Fahrenheit"""
        temp = self.system_info_f.get_cpu_temp()
        self.assertEqual(temp, 113.0)  # 45°C = 113°F
    
    @patch('builtins.open', side_effect=Exception('File not found'))
    def test_get_cpu_temp_error(self, mock_file):
        """Test CPU temperature error handling"""
        temp = self.system_info_c.get_cpu_temp()
        self.assertEqual(temp, 0)
    
    @patch('builtins.open', mock_open(read_data='cpu  100 0 50 850 0 0 0 0 0 0\n'))
    def test_get_cpu_usage_first_call(self):
        """Test CPU usage on first call (should return 0)"""
        usage = self.system_info_c.get_cpu_usage()
        self.assertEqual(usage, 0)
    
    @patch('builtins.open')
    def test_get_cpu_usage_second_call(self, mock_file):
        """Test CPU usage calculation on second call"""
        # First call
        mock_file.return_value.__enter__.return_value.readline.return_value = 'cpu  100 0 50 850 0 0 0 0 0 0\n'
        self.system_info_c.get_cpu_usage()
        
        # Second call with increased values
        mock_file.return_value.__enter__.return_value.readline.return_value = 'cpu  120 0 60 860 0 0 0 0 0 0\n'
        usage = self.system_info_c.get_cpu_usage()
        
        # CPU usage should be calculated
        self.assertGreater(usage, 0)
        self.assertLessEqual(usage, 100)
    
    @patch('builtins.open', side_effect=Exception('Error'))
    def test_get_cpu_usage_error(self, mock_file):
        """Test CPU usage error handling"""
        usage = self.system_info_c.get_cpu_usage()
        self.assertEqual(usage, 0)
    
    @patch('builtins.open')
    def test_get_memory_usage(self, mock_file):
        """Test memory usage calculation"""
        mock_data = 'MemTotal:       8000000 kB\nMemAvailable:   4000000 kB\n'
        mock_file.return_value.__enter__.return_value.readlines.return_value = mock_data.split('\n')
        
        mem_used, mem_total, mem_percent = self.system_info_c.get_memory_usage()
        
        self.assertAlmostEqual(mem_used, 3906.25, places=1)  # ~4GB used
        self.assertAlmostEqual(mem_total, 7812.5, places=1)  # ~8GB total
        self.assertEqual(mem_percent, 50.0)  # 50% used
    
    @patch('builtins.open', side_effect=Exception('Error'))
    def test_get_memory_usage_error(self, mock_file):
        """Test memory usage error handling"""
        mem_used, mem_total, mem_percent = self.system_info_c.get_memory_usage()
        self.assertEqual(mem_used, 0)
        self.assertEqual(mem_total, 0)
        self.assertEqual(mem_percent, 0)
    
    def test_get_disk_usage(self):
        """Test disk usage calculation"""
        # Mock statvfs result
        class MockStatVFS:
            f_blocks = 10000000  # Total blocks
            f_frsize = 4096      # Block size
            f_bavail = 5000000   # Available blocks
        
        # Only patch if statvfs exists (Unix-like systems)
        if hasattr(os, 'statvfs'):
            with patch('os.statvfs', return_value=MockStatVFS()):
                disk_used, disk_total, disk_percent = self.system_info_c.get_disk_usage()
                
                self.assertAlmostEqual(disk_used, 19.073, places=2)  # ~19GB used
                self.assertAlmostEqual(disk_total, 38.147, places=2)  # ~38GB total
                self.assertEqual(disk_percent, 50.0)  # 50% used
        else:
            # On Windows, just test that it returns the error tuple
            disk_used, disk_total, disk_percent = self.system_info_c.get_disk_usage()
            self.assertEqual(disk_used, 0)
            self.assertEqual(disk_total, 0)
            self.assertEqual(disk_percent, 0)
    
    def test_get_disk_usage_error(self):
        """Test disk usage error handling"""
        # Test by passing invalid path if statvfs exists
        if hasattr(os, 'statvfs'):
            with patch('os.statvfs', side_effect=Exception('Error')):
                disk_used, disk_total, disk_percent = self.system_info_c.get_disk_usage()
                self.assertEqual(disk_used, 0)
                self.assertEqual(disk_total, 0)
                self.assertEqual(disk_percent, 0)
        else:
            # On Windows, it will return 0,0,0 anyway
            disk_used, disk_total, disk_percent = self.system_info_c.get_disk_usage()
            self.assertEqual(disk_used, 0)
            self.assertEqual(disk_total, 0)
            self.assertEqual(disk_percent, 0)


if __name__ == '__main__':
    unittest.main()
