"""Tests for the time_utils module."""

import pytest
from datetime import datetime
from time_utils import parse_time_input, format_time_for_display, calculate_ping_deadline_time


@pytest.mark.parametrize("input_str, expected", [
    ('10 AM',    (10, 0)),
    ('9pm',      (21, 0)),
    ('22:00',    (22, 0)),
    ('3:30 PM',  (15, 30)),
    ('12 AM',    (0, 0)),
    ('12 PM',    (12, 0)),
    ('10',       (10, 0)),
])
def test_parse_time_input(input_str, expected):
    assert parse_time_input(input_str) == expected


@pytest.mark.parametrize("input_str", ['invalid', '25:00', '', '25', '2200'])
def test_parse_rejects_invalid(input_str):
    assert parse_time_input(input_str) is None


@pytest.mark.parametrize("hour, minute, expected", [
    (10, 0,  '10 AM'),
    (14, 0,  '2 PM'),
    (0,  0,  '12 AM'),
    (12, 0,  '12 PM'),
    (15, 30, '3:30 PM'),
])
def test_format_time_for_display(hour, minute, expected):
    assert format_time_for_display(hour, minute) == expected


def test_deadline_adds_hours():
    result = calculate_ping_deadline_time(14, 0, 3)
    assert result.hour == 17 and result.minute == 0
    assert isinstance(result, datetime)
