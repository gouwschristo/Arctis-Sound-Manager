# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
The Arctis Pro GameDAC had one setting, a 0-10 sidetone slider. GG's page for
it offers four sidetone levels, the DAC gain, line out with a four-channel
stream mix, and the screen brightness; the commands come from the spec
(arctis-pro-gameDac.device), the values from GG 122's UI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ruamel.yaml import YAML

from arctis_sound_manager.config import DeviceConfiguration
from arctis_sound_manager.core import CoreEngine

DEVICES_DIR = Path(__file__).parent.parent / "src" / "arctis_sound_manager" / "devices"


def _gamedac() -> tuple[DeviceConfiguration, MagicMock]:
    cfg = DeviceConfiguration(YAML(typ="safe").load(DEVICES_DIR / "arctis_pro_gamedac.yaml"))
    engine = MagicMock()
    engine.device_config = cfg
    engine.device_settings.settings = {}
    engine.device_settings.get.side_effect = (
        lambda name, default=0: engine.device_settings.settings.get(name, default))
    return cfg, engine


def _setting(cfg: DeviceConfiguration, name: str):
    return next(c for section in cfg.settings.values() for c in section if c.name == name)


def _frame(engine: MagicMock, cfg: DeviceConfiguration, name: str, value: int) -> list[int]:
    return CoreEngine._resolve_update_sequence(engine, _setting(cfg, name), value)


def test_sidetone_offers_ggs_four_levels():
    cfg, engine = _gamedac()
    sidetone = _setting(cfg, "mic_side_tone")

    assert sorted(sidetone.values_mapping) == [0, 1, 2, 3]
    assert _frame(engine, cfg, "mic_side_tone", 3) == [0x39, 3]


def test_gain_and_line_out_are_single_byte_commands():
    cfg, engine = _gamedac()

    assert _frame(engine, cfg, "gain", 0x01) == [0x27, 0x01]
    assert _frame(engine, cfg, "line_out", 0x02) == [0x43, 0x02]
    assert _frame(engine, cfg, "station_screen_brightness", 120) == [0x85, 120]


def test_each_stream_mix_slider_sends_all_four_levels():
    """stream_mix (0x47) is game, chat, aux, mic in one frame."""
    cfg, engine = _gamedac()
    engine.device_settings.settings.update({
        "line_out_stream_game_volume": 20, "line_out_stream_chat_volume": 15,
        "line_out_stream_aux_volume": 10, "line_out_stream_mic_volume": 5})

    assert _frame(engine, cfg, "line_out_stream_game_volume", 12) == [0x47, 12, 15, 10, 5]
    assert _frame(engine, cfg, "line_out_stream_chat_volume", 12) == [0x47, 20, 12, 10, 5]
    assert _frame(engine, cfg, "line_out_stream_aux_volume", 12) == [0x47, 20, 15, 12, 5]
    assert _frame(engine, cfg, "line_out_stream_mic_volume", 12) == [0x47, 20, 15, 10, 12]
