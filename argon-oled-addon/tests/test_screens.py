"""
Unit tests for screens module
"""

import unittest
from unittest.mock import Mock, MagicMock, patch

try:
    from PIL import ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    ImageFont = None

try:
    from screens import ScreenRenderer
    SCREENS_AVAILABLE = True
except ImportError:
    SCREENS_AVAILABLE = False
    ScreenRenderer = None


@unittest.skipUnless(PIL_AVAILABLE and SCREENS_AVAILABLE, "PIL and screens module required")
class TestScreenRenderer(unittest.TestCase):
    """Test ScreenRenderer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_device = Mock()
        self.fonts = {
            'small': ImageFont.load_default(),
            'medium': ImageFont.load_default(),
            'large': ImageFont.load_default()
        }
        self.renderer = ScreenRenderer(
            device=self.mock_device,
            fonts=self.fonts,
            temp_unit='C',
            logo_image=None
        )
    
    def test_init(self):
        """Test ScreenRenderer initialization"""
        self.assertEqual(self.renderer.device, self.mock_device)
        self.assertEqual(self.renderer.temp_unit, 'C')
        self.assertIsNone(self.renderer.logo_image)
    
    def test_draw_header(self):
        """Test draw_header method"""
        mock_draw = Mock()
        
        self.renderer.draw_header(mock_draw, "Test Header", "🔧")
        
        # Verify header rectangle and text were drawn
        self.assertTrue(mock_draw.rectangle.called)
        self.assertTrue(mock_draw.text.called)
    
    def test_draw_progress_bar_solid(self):
        """Test draw_progress_bar with solid style"""
        mock_draw = Mock()
        
        self.renderer.draw_progress_bar(mock_draw, 10, 20, 100, 8, 50, "solid")
        
        # Verify rectangles were drawn
        self.assertTrue(mock_draw.rectangle.called)
        self.assertGreaterEqual(mock_draw.rectangle.call_count, 2)
    
    def test_draw_progress_bar_striped(self):
        """Test draw_progress_bar with striped style"""
        mock_draw = Mock()
        
        self.renderer.draw_progress_bar(mock_draw, 10, 20, 100, 8, 50, "striped")
        
        # Verify lines were drawn
        self.assertTrue(mock_draw.line.called)
    
    def test_draw_progress_bar_warning(self):
        """Test draw_progress_bar with warning indicator"""
        mock_draw = Mock()
        
        self.renderer.draw_progress_bar(mock_draw, 10, 20, 100, 8, 85, "solid")
        
        # Verify warning indicator drawn (extra rectangle)
        self.assertGreaterEqual(mock_draw.rectangle.call_count, 3)
    
    def test_draw_segment_digit_valid(self):
        """Test _draw_segment_digit with valid digit"""
        mock_draw = Mock()
        
        self.renderer._draw_segment_digit(mock_draw, 10, 20, 8, scale=1.0)
        
        # Verify segments were drawn (digit 8 has all 7 segments)
        self.assertEqual(mock_draw.rectangle.call_count, 7)
    
    def test_draw_segment_digit_invalid(self):
        """Test _draw_segment_digit with invalid digit"""
        mock_draw = Mock()
        
        self.renderer._draw_segment_digit(mock_draw, 10, 20, 99, scale=1.0)
        
        # Should not draw anything for invalid digit
        self.assertFalse(mock_draw.rectangle.called)
    
    @patch('screens.canvas')
    @patch('screens.datetime')
    def test_draw_clock(self, mock_datetime, mock_canvas):
        """Test draw_clock method"""
        # Mock datetime
        mock_now = Mock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%b %d, %Y": "Nov 20, 2025",
            "%H": "14",
            "%M": "30",
            "%S": "45"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # Mock canvas context manager
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        self.renderer.draw_clock()
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify drawing occurred
        self.assertTrue(mock_draw.rectangle.called)
    
    @patch('screens.canvas')
    def test_draw_cpu(self, mock_canvas):
        """Test draw_cpu method"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_system_info = Mock()
        mock_system_info.get_cpu_usage.return_value = 45.5
        mock_system_info.get_cpu_temp.return_value = 55.0
        
        self.renderer.draw_cpu(mock_system_info)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify system info was queried
        mock_system_info.get_cpu_usage.assert_called_once()
        mock_system_info.get_cpu_temp.assert_called_once()
    
    @patch('screens.canvas')
    def test_draw_ram(self, mock_canvas):
        """Test draw_ram method"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_system_info = Mock()
        mock_system_info.get_memory_usage.return_value = (50.0, 8.0)
        
        self.renderer.draw_ram(mock_system_info)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify system info was queried
        mock_system_info.get_memory_usage.assert_called_once()
    
    @patch('screens.canvas')
    def test_draw_storage(self, mock_canvas):
        """Test draw_storage method"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_system_info = Mock()
        mock_system_info.get_disk_usage.return_value = (75.0, 32.0)
        
        self.renderer.draw_storage(mock_system_info)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify system info was queried
        mock_system_info.get_disk_usage.assert_called_once()
    
    @patch('screens.canvas')
    def test_draw_temp_normal(self, mock_canvas):
        """Test draw_temp with normal temperature"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_system_info = Mock()
        mock_system_info.get_cpu_temp.return_value = 45.0
        
        self.renderer.draw_temp(mock_system_info)
        
        # Verify canvas was used and text drawn
        mock_canvas.assert_called_once_with(self.mock_device)
        self.assertTrue(mock_draw.text.called)
    
    @patch('screens.canvas')
    def test_draw_ip(self, mock_canvas):
        """Test draw_ip method"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_supervisor_api = Mock()
        mock_supervisor_api.get_ip_address.return_value = "192.168.1.100"
        
        self.renderer.draw_ip(mock_supervisor_api)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify API was queried
        mock_supervisor_api.get_ip_address.assert_called_once()
    
    @patch('screens.canvas')
    def test_draw_logo_text(self, mock_canvas):
        """Test draw_logo with text (no image)"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        self.renderer.draw_logo()
        
        # Verify canvas was used and text drawn
        mock_canvas.assert_called_once_with(self.mock_device)
        self.assertTrue(mock_draw.text.called)
        self.assertTrue(mock_draw.rectangle.called)
    
    @patch('screens.canvas')
    @patch('screens.qrcode.QRCode')
    def test_draw_qr_success(self, mock_qrcode_class, mock_canvas):
        """Test draw_qr with successful QR generation"""
        mock_draw = Mock()
        mock_draw._image = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_supervisor_api = Mock()
        mock_supervisor_api.get_ha_url.return_value = "http://homeassistant.local:8123"
        
        # Mock QR code
        mock_qr = Mock()
        mock_qr_img = Mock()
        mock_qr_img.resize.return_value = mock_qr_img
        mock_qr.make_image.return_value = mock_qr_img
        mock_qrcode_class.return_value = mock_qr
        
        self.renderer.draw_qr(mock_supervisor_api)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify QR code was generated
        mock_qr.add_data.assert_called_once()
        mock_qr.make.assert_called_once()
    
    @patch('screens.canvas')
    def test_draw_qr_no_url(self, mock_canvas):
        """Test draw_qr with no URL available"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_supervisor_api = Mock()
        mock_supervisor_api.get_ha_url.return_value = None
        
        self.renderer.draw_qr(mock_supervisor_api)
        
        # Verify error message drawn
        self.assertTrue(mock_draw.text.called)
    
    @patch('screens.canvas')
    def test_draw_ha_status(self, mock_canvas):
        """Test draw_ha_status method"""
        mock_draw = Mock()
        mock_canvas.return_value.__enter__.return_value = mock_draw
        
        mock_supervisor_api = Mock()
        mock_supervisor_api.get_ha_system_status.return_value = {
            'updates': 2,
            'repairs': 0,
            'last_backup': '2025-11-20T10:00:00+00:00',
            'backup_state': 'OK'
        }
        
        self.renderer.draw_ha_status(mock_supervisor_api)
        
        # Verify canvas was used
        mock_canvas.assert_called_once_with(self.mock_device)
        # Verify API was queried
        mock_supervisor_api.get_ha_system_status.assert_called_once()


if __name__ == '__main__':
    unittest.main()
