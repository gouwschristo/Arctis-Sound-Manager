# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GG offers the microphone volume on the Arctis 7 and Arctis 1 Wireless
dongles: mic_volume (0x33) in arctis7dongle and arctis-1w-tx,
[0x06, 0x33, 0x00, amplitude 0-100].
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ruamel.yaml import YAML

from arctis_sound_manager.config import DeviceConfiguration
from arctis_sound_manager.core import CoreEngine

DEVICES_DIR = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"


@pytest.mark.parametrize("profile", ["arctis_7.yaml", "arctis_1_wireless.yaml"])
def test_mic_volume_sends_the_amplitude(profile):
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / profile))
    setting = next(c for section in cfg.settings.values() for c in section if c.name == "mic_volume")

    assert (setting.min, setting.max) == (0, 100)
    assert CoreEngine._resolve_update_sequence(MagicMock(), setting, 75) == [0x06, 0x33, 0x00, 75]
