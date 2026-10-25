# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
The Nova Pro Wired had gain, mic volume and sidetone. GG's page for its
GameDAC also offers line out with a main / aux / mic stream mix and the
screen's dim timer (base_arctis_nova_pro: 0x43, 0x47, 0x83).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ruamel.yaml import YAML

from arctis_sound_manager.config import DeviceConfiguration
from arctis_sound_manager.core import CoreEngine

DEVICES_DIR = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"


def _setup():
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / "arctis_nova_pro_wired.yaml"))
    engine = MagicMock()
    engine.device_settings.settings = {"line_out_stream_main_volume": 80,
                                       "line_out_stream_aux_volume": 60,
                                       "line_out_stream_mic_volume": 40}
    engine.device_settings.get.side_effect = (
        lambda name, default=0: engine.device_settings.settings.get(name, default))
    return cfg, engine


def _frame(name: str, value: int) -> list[int]:
    cfg, engine = _setup()
    setting = next(c for section in cfg.settings.values() for c in section if c.name == name)
    return CoreEngine._resolve_update_sequence(engine, setting, value)


def test_line_out_mode():
    assert _frame("line_out", 2) == [0x06, 0x43, 2]


def test_stream_mix_is_main_main_aux_mic():
    """main, the spec's unused byte (main again, as on the Nova Pro
    Wireless), aux, mic."""
    assert _frame("line_out_stream_main_volume", 50) == [0x06, 0x47, 50, 50, 60, 40]
    assert _frame("line_out_stream_aux_volume", 50) == [0x06, 0x47, 80, 80, 50, 40]
    assert _frame("line_out_stream_mic_volume", 50) == [0x06, 0x47, 80, 80, 60, 50]


def test_the_dim_timer_takes_minutes_not_an_index():
    assert _frame("station_screen_saver_timeout", 30) == [0x06, 0x83, 30]
