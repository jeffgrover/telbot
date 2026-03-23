"""
Unit tests for time_utils module.
"""
import pytest
from datetime import datetime, timedelta

from time_utils import (
    parse_time_input,
    format_time_for_display,
    calculate_deadline_time,
)


class TestTimeParsing:
    """Tests for parse_time_input function."""
    
    @pytest.mark.parametrize("input_str, expected", [
        ('10 AM', (10, 0)),
        ('10:30 AM', (10, 30)),  # Now supports minutes with colon
        ('10 PM', (22, 0)),
        ('9 PM', (21, 0)),
        ('9pm', (21, 0)),
        ('9AM', (9, 0)),
        ('9am', (9, 0)),
        ('22:00', (22, 0)),
        ('2200', None),  # Should fail without colon
        ('15:45', (15, 45)),
        ('3:30 PM', (15, 30)),
        ('12:00 AM', (0, 0)),  # Now supports midnight with minutes
        ('12:00 PM', (12, 0)),  # Now supports noon with minutes
    ])
    def test_parse_time_input(self, input_str, expected):
        """Test parsing various time formats."""
        result = parse_time_input(input_str)
        assert result == expected, f"parse_time_input('{input_str}') returned {result}, expected {expected}"
    
    def test_parse_invalid_formats(self):
        """Test that invalid formats return None."""
        invalid_formats = ['invalid', '25:00', '', 'abc']
        for fmt in invalid_formats:
            result = parse_time_input(fmt)
            assert result is None, f"parse_time_input('{fmt}') should return None, got {result}"
    
    def test_parse_valid_24_hour_formats(self):
        """Test that valid 24-hour formats are parsed correctly."""
        valid_formats = {
            '13:00': (13, 0),
            '15:30': (15, 30),
            '23:45': (23, 45),
        }
        for fmt, expected in valid_formats.items():
            result = parse_time_input(fmt)
            assert result == expected, f"parse_time_input('{fmt}') returned {result}, expected {expected}"


class TestTimeFormatting:
    """Tests for format_time_for_display function."""
    
    @pytest.mark.parametrize("input_tuple, expected", [
        ((10, 0), '10 AM'),
        ((14, 0), '2 PM'),
        ((23, 0), '11 PM'),
        ((0, 0), '12 AM'),
        ((12, 0), '12 PM'),
        ((15, 30), '3:30 PM'),
        ((9, 45), '9:45 AM'),
        ((21, 15), '9:15 PM'),
    ])
    def test_format_time_for_display(self, input_tuple, expected):
        """Test formatting various times."""
        result = format_time_for_display(*input_tuple)
        assert result == expected, f"format_time_for_display{input_tuple} returned '{result}', expected '{expected}'"


class TestDeadlineCalculation:
    """Tests for calculate_deadline_time function."""
    
    def test_calculate_deadline_same_day(self):
        """Test deadline calculation when preferred time is in future."""
        # Mock current time to make test deterministic
        mock_now = datetime(2024, 1, 15, 10, 30)
        
        # Preferred time is 2 PM (14:00), delay 3 hours = 5 PM (17:00)
        result = calculate_deadline_time(14, 0, 3)
        assert result == '5 PM', f"Expected '5 PM', got '{result}'"
    
    def test_calculate_deadline_next_day(self):
        """Test deadline calculation when preferred time has passed."""
        # Mock current time to make test deterministic
        mock_now = datetime(2024, 1, 15, 15, 30)
        
        # Preferred time is 10 AM (10:00), delay 3 hours = 1 PM (13:00)
        result = calculate_deadline_time(10, 0, 3)
        assert result == '1 PM', f"Expected '1 PM', got '{result}'"
    
    def test_calculate_deadline_with_minutes(self):
        """Test deadline calculation with minutes."""
        # Mock current time
        mock_now = datetime(2024, 1, 15, 9, 30)
        
        # Preferred time is 9:30 AM, delay 2 hours = 11:30 AM
        result = calculate_deadline_time(9, 30, 2)
        assert result == '11:30 AM', f"Expected '11:30 AM', got '{result}'"
    
    def test_calculate_deadline_midnight(self):
        """Test deadline calculation crossing midnight."""
        # Mock current time
        mock_now = datetime(2024, 1, 15, 23, 30)
        
        # Preferred time is 11 PM (23:00), delay 2 hours = 1 AM next day
        result = calculate_deadline_time(23, 0, 2)
        assert result == '1 AM', f"Expected '1 AM', got '{result}'"


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_midnight_boundary(self):
        """Test formatting midnight correctly."""
        result = format_time_for_display(0, 0)
        assert result == '12 AM', f"Expected '12 AM' for midnight, got '{result}'"
    
    def test_noon_boundary(self):
        """Test formatting noon correctly."""
        result = format_time_for_display(12, 0)
        assert result == '12 PM', f"Expected '12 PM' for noon, got '{result}'"
    
    def test_24_hour_boundary(self):
        """Test formatting 24:00 as midnight."""
        result = format_time_for_display(24, 0)
        assert result == '12 AM', f"Expected '12 AM' for 24:00, got '{result}'"
    
    def test_max_hour(self):
        """Test formatting hour 23."""
        result = format_time_for_display(23, 0)
        assert result == '11 PM', f"Expected '11 PM' for hour 23, got '{result}'"
