# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GameBuds: which link the earbuds play from, audio_mode (0xAA) in
base_arctis_gamebuds_dongle — 0 the 2.4 GHz dongle, 1 Bluetooth. GG sends
it when its EQ panel switches between the Wireless and Bluetooth tabs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ruamel.yaml import YAML

from arctis_sound_manager.config import DeviceConfiguration
from arctis_sound_manager.core import CoreEngine

DEVICES_DIR = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"


def test_audio_source_sends_audio_mode():
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / "gamebuds.yaml"))
    setting = next(c for section in cfg.settings.values() for c in section if c.name == "audio_source")

    assert sorted(setting.values_mapping) == [0, 1]
    assert CoreEngine._resolve_update_sequence(MagicMock(), setting, 1) == [0xAA, 1]
