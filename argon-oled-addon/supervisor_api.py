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
    
    def get_ip_address(self):
        """Get host IP address from Supervisor API"""
        try:
            network_info = self.get_network_info()
            interfaces = network_info.get('interfaces', [])
            
            # Try to get the primary interface IP
            for interface in interfaces:
                if interface.get('primary', False):
                    ipv4 = interface.get('ipv4', {})
                    addresses = ipv4.get('address', [])
                    if addresses:
                        # Return the first address without CIDR notation
                        ip = addresses[0].split('/')[0]
                        return ip
            
            # Fallback: get any non-docker interface
            for interface in interfaces:
                if not interface.get('interface', '').startswith('docker'):
                    ipv4 = interface.get('ipv4', {})
                    addresses = ipv4.get('address', [])
                    if addresses:
                        ip = addresses[0].split('/')[0]
                        return ip
        except Exception as e:
            self._log(f"Could not get IP from Supervisor API: {e}")
        
        # Final fallback to socket method
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "No Network"
    
    def get_ha_url(self):
        """Get Home Assistant URL"""
        try:
            # Try to get configured URL from homeassistant
            ha_info = self.get_homeassistant_info()
            
            # Check for external/internal URL in the config
            external_url = ha_info.get('external_url')
            internal_url = ha_info.get('internal_url')
            
            if external_url:
                return external_url
            if internal_url:
                return internal_url
        except Exception as e:
            self._log(f"Could not get HA URL from API: {e}")
        
        # Fallback to IP-based URL using host IP
        ip = self.get_ip_address()
        if ip != "No Network":
            return f"http://{ip}:8123"
        
        return None
    
    def get_ha_system_status(self):
        """Get Home Assistant system status information"""
        status_info = {
            'updates': 0,
            'repairs': 0,
            'last_backup': None,
            'backup_state': 'Unknown'
        }
        
        try:
            # Get supervisor updates
            supervisor_info = self.get_supervisor_info()
            if supervisor_info.get('update_available', False):
                status_info['updates'] += 1
            
            # Get core updates
            core_info = self.get_core_info()
            if core_info.get('update_available', False):
                status_info['updates'] += 1
            
            # Get addon updates
            addons = self.get_addons()
            for addon in addons:
                if addon.get('update_available', False):
                    status_info['updates'] += 1
            
            # Get backup info
            backups = self.get_backups()
            self._log(f"Found {len(backups)} backups")
            if backups:
                # Sort by date and get most recent
                sorted_backups = sorted(backups, key=lambda x: x.get('date', ''), reverse=True)
                latest = sorted_backups[0]
                self._log(f"Latest backup data: {latest}")
                status_info['last_backup'] = latest.get('date', 'Unknown')
                status_info['backup_state'] = 'OK'
            else:
                status_info['backup_state'] = 'None'
        except Exception as e:
            self._log(f"Error getting HA system status: {e}")
        
        return status_info
    
    def reboot_host(self):
        """Reboot the host system"""
        response = self.request('host/reboot', method='POST', timeout=10)
        return response is not None and response.status_code in [200, 202]
    
    def shutdown_host(self):
        """Shutdown the host system"""
        response = self.request('host/shutdown', method='POST', timeout=10)
        return response is not None and response.status_code in [200, 202]
