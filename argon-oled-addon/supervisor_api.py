"""
Home Assistant Supervisor API client
Handles all communication with the Supervisor API
"""

import os
import requests


SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')


class SupervisorAPI:
    """Client for Home Assistant Supervisor API"""
    
    def __init__(self, debug_callback=None):
        self.debug_callback = debug_callback
    
    def _log(self, message):
        """Log debug message if callback is set"""
        if self.debug_callback:
            self.debug_callback(message)
    
    def request(self, endpoint, method='GET', timeout=5):
        """Make a request to the Supervisor API with standard error handling"""
        try:
            headers = {
                'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
                'Content-Type': 'application/json'
            }
            url = f'http://supervisor/{endpoint}'
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, timeout=timeout)
            else:
                return None
            
            return response
        except requests.exceptions.Timeout:
            self._log(f"{method} request to {endpoint} timed out")
            return None
        except Exception as e:
            self._log(f"{method} request to {endpoint} failed: {e}")
            return None
    
    def check_power_permissions(self):
        """Check if addon has permissions to reboot/shutdown the host
        Returns: (enabled, message)
        """
        if not SUPERVISOR_TOKEN:
            return False, "No supervisor token available"
        
        # Try to get supervisor info
        response = self.request('supervisor/info')
        
        if response and response.status_code == 200:
            # Test if we can access host endpoints (requires manager role)
            test_response = self.request('host/info')
            
            if test_response and test_response.status_code == 200:
                return True, "Addon has host control permissions"
            elif test_response and test_response.status_code == 403:
                return False, "Addon lacks 'manager' role permissions"
            else:
                return False, "Unexpected response from host endpoint"
        else:
            return False, "Cannot access supervisor API"
    
    def get_network_info(self):
        """Get network information including IP addresses"""
        response = self.request('network/info')
        if response and response.status_code == 200:
            return response.json().get('data', {})
        return {}
    
    def get_homeassistant_info(self):
        """Get Home Assistant info including URLs"""
        response = self.request('homeassistant/info')
        if response and response.status_code == 200:
            return response.json().get('data', {})
        return {}
    
    def get_core_info(self):
        """Get Home Assistant core info"""
        response = self.request('core/info')
        if response and response.status_code == 200:
            return response.json().get('data', {})
        return {}
    
    def get_supervisor_info(self):
        """Get supervisor info"""
        response = self.request('supervisor/info')
        if response and response.status_code == 200:
            return response.json().get('data', {})
        return {}
    
    def get_addons(self):
        """Get list of addons"""
        response = self.request('addons')
        if response and response.status_code == 200:
            return response.json().get('data', {}).get('addons', [])
        return []
    
    def get_backups(self):
        """Get list of backups"""
        response = self.request('backups')
        if response and response.status_code == 200:
            return response.json().get('data', {}).get('backups', [])
        return []
    
    def reboot_host(self):
        """Reboot the host system"""
        return self.request('host/reboot', method='POST', timeout=10)
    
    def shutdown_host(self):
        """Shutdown the host system"""
        return self.request('host/shutdown', method='POST', timeout=10)
