"""
Unit tests for supervisor_api module
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
from supervisor_api import SupervisorAPI


class TestSupervisorAPI(unittest.TestCase):
    """Test SupervisorAPI class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.debug_messages = []
        
        def debug_callback(msg):
            self.debug_messages.append(msg)
        
        self.api = SupervisorAPI(debug_callback=debug_callback)
    
    def test_init(self):
        """Test SupervisorAPI initialization"""
        self.assertIsNotNone(self.api.debug_callback)
    
    def test_init_without_callback(self):
        """Test SupervisorAPI initialization without debug callback"""
        api = SupervisorAPI()
        self.assertIsNone(api.debug_callback)
    
    @patch('supervisor_api.requests.get')
    def test_request_get_success(self, mock_get):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response
        
        response = self.api.request('test/endpoint')
        
        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once()
    
    @patch('supervisor_api.requests.post')
    def test_request_post_success(self, mock_post):
        """Test successful POST request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        response = self.api.request('test/endpoint', method='POST')
        
        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
    
    @patch('supervisor_api.requests.get')
    def test_request_timeout(self, mock_get):
        """Test request timeout handling"""
        mock_get.side_effect = Exception('Timeout')
        
        response = self.api.request('test/endpoint')
        
        self.assertIsNone(response)
        self.assertTrue(any('failed' in msg for msg in self.debug_messages))
    
    @patch('supervisor_api.SUPERVISOR_TOKEN', 'test_token')
    @patch('supervisor_api.requests.get')
    def test_check_power_permissions_enabled(self, mock_get):
        """Test power permissions check when enabled"""
        # Mock supervisor/info response
        mock_supervisor_response = Mock()
        mock_supervisor_response.status_code = 200
        mock_supervisor_response.json.return_value = {'data': {}}
        
        # Mock host/info response (success = has permissions)
        mock_host_response = Mock()
        mock_host_response.status_code = 200
        mock_host_response.json.return_value = {'data': {}}
        
        mock_get.side_effect = [mock_supervisor_response, mock_host_response]
        
        enabled, message = self.api.check_power_permissions()
        
        self.assertTrue(enabled)
        self.assertIn('permissions', message.lower())
    
    @patch('supervisor_api.SUPERVISOR_TOKEN', 'test_token')
    @patch('supervisor_api.requests.get')
    def test_check_power_permissions_forbidden(self, mock_get):
        """Test power permissions check when forbidden"""
        # Mock supervisor/info response
        mock_supervisor_response = Mock()
        mock_supervisor_response.status_code = 200
        
        # Mock host/info response (403 = no permissions)
        mock_host_response = Mock()
        mock_host_response.status_code = 403
        
        mock_get.side_effect = [mock_supervisor_response, mock_host_response]
        
        enabled, message = self.api.check_power_permissions()
        
        self.assertFalse(enabled)
        self.assertIn('manager', message.lower())
    
    @patch('supervisor_api.requests.post')
    def test_reboot_host_success(self, mock_post):
        """Test successful reboot command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = self.api.reboot_host()
        
        self.assertTrue(success)
    
    @patch('supervisor_api.requests.post')
    def test_reboot_host_failure(self, mock_post):
        """Test failed reboot command"""
        mock_post.return_value = None
        
        success = self.api.reboot_host()
        
        self.assertFalse(success)
    
    @patch('supervisor_api.requests.post')
    def test_shutdown_host_success(self, mock_post):
        """Test successful shutdown command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = self.api.shutdown_host()
        
        self.assertTrue(success)
    
    @patch('supervisor_api.requests.get')
    def test_get_ip_address_from_network(self, mock_get):
        """Test getting IP address from network API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'interfaces': [
                    {
                        'primary': True,
                        'ipv4': {
                            'address': ['192.168.1.100/24']
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        ip = self.api.get_ip_address()
        
        self.assertEqual(ip, '192.168.1.100')
    
    @patch('supervisor_api.requests.get')
    @patch('socket.socket')
    def test_get_ip_address_fallback(self, mock_socket, mock_get):
        """Test IP address fallback to socket method"""
        mock_get.return_value = None
        
        # Mock socket
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ['10.0.0.5', 0]
        mock_socket.return_value = mock_sock
        
        ip = self.api.get_ip_address()
        
        self.assertEqual(ip, '10.0.0.5')
    
    @patch('supervisor_api.SupervisorAPI.get_homeassistant_info')
    def test_get_ha_url_external(self, mock_get_ha_info):
        """Test getting HA URL with external URL configured"""
        # Mock homeassistant/info response with external URL
        mock_get_ha_info.return_value = {
            'external_url': 'https://mydomain.com'
        }
        
        url = self.api.get_ha_url()
        
        self.assertEqual(url, 'https://mydomain.com')
    
    @patch('supervisor_api.requests.get')
    def test_get_ha_system_status(self, mock_get):
        """Test getting HA system status"""
        # Mock supervisor/info
        mock_supervisor = Mock()
        mock_supervisor.status_code = 200
        mock_supervisor.json.return_value = {'data': {'update_available': False}}
        
        # Mock core/info
        mock_core = Mock()
        mock_core.status_code = 200
        mock_core.json.return_value = {'data': {'update_available': True}}
        
        # Mock addons
        mock_addons = Mock()
        mock_addons.status_code = 200
        mock_addons.json.return_value = {
            'data': {
                'addons': [
                    {'update_available': True},
                    {'update_available': False}
                ]
            }
        }
        
        # Mock backups
        mock_backups = Mock()
        mock_backups.status_code = 200
        mock_backups.json.return_value = {
            'data': {
                'backups': [
                    {'date': '2025-11-20T10:00:00+00:00'}
                ]
            }
        }
        
        mock_get.side_effect = [mock_supervisor, mock_core, mock_addons, mock_backups]
        
        status = self.api.get_ha_system_status()
        
        self.assertEqual(status['updates'], 2)  # core + 1 addon
        self.assertEqual(status['backup_state'], 'OK')
        self.assertIsNotNone(status['last_backup'])


if __name__ == '__main__':
    unittest.main()
