# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
The Arctis Pro Wireless had sidetone, auto-off and the screen brightness.
GG's page for this base station also offers the volume limiter, the muted
mic LED, the screensaver and its delay, and two Bluetooth preferences. Every
write is [command, 0xAA, value]: the spec's error-check byte, the same frame
the existing three already send.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ruamel.yaml import YAML

from arctis_sound_manager.config import DeviceConfiguration
from arctis_sound_manager.core import CoreEngine

DEVICES_DIR = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"


@pytest.mark.parametrize("name, value, frame", [
    ("volume_limiter", 1, [0x27, 0xAA, 1]),
    ("mic_led_brightness", 7, [0x3E, 0xAA, 7]),
    ("station_screensaver", 2, [0x89, 0xAA, 2]),
    ("station_screen_saver_timeout", 60, [0x60, 0xAA, 60]),
    ("bluetooth_power_status", 1, [0x62, 0xAA, 1]),
    ("bluetooth_auto_mute", 1, [0x63, 0xAA, 1]),
])
def test_each_new_setting_sends_the_spec_frame(name, value, frame):
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / "arctis_pro_wireless.yaml"))
    setting = next(c for section in cfg.settings.values() for c in section if c.name == name)

    assert CoreEngine._resolve_update_sequence(MagicMock(), setting, value) == frame


def test_the_screen_delay_spans_ggs_range():
    """display_timeout counts tens of seconds, 3 to 60: 30 s to 10 min."""
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / "arctis_pro_wireless.yaml"))
    delay = next(c for section in cfg.settings.values() for c in section
                 if c.name == "station_screen_saver_timeout")

    assert (delay.min, delay.max) == (3, 60)
