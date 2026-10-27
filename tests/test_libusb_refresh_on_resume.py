# Copyright (C) 2026 loteran
# SPDX-License-Identifier: GPL-3.0-or-later
"""
After a resume on SteamOS (distrobox), the Nova Pro Wireless came back —
`lsusb` listed it — but ASM said "not currently connected" until the
service restarted (#325). libusb with hotplug support never rescans the bus;
its device list only follows hotplug events, and that one never reached the
container. When the kernel lists a headset libusb does not, ASM now opens a
fresh libusb context and looks again.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import usb.backend.libusb1 as libusb1

from arctis_sound_manager.usb_reenumerate import refresh_libusb_context, sysfs_has_device


def _sysfs(tmp_path: Path, devices: dict[str, tuple[str, str]]) -> Path:
    for name, (vendor, product) in devices.items():
        d = tmp_path / name
        d.mkdir()
        (d / "idVendor").write_text(vendor + "\n")
        (d / "idProduct").write_text(product + "\n")
    (tmp_path / "1-0:1.0").mkdir()  # an interface entry: no idVendor
    return tmp_path


def test_sysfs_has_device_finds_the_dongle(tmp_path):
    root = _sysfs(tmp_path, {"1-3": ("1038", "12e0"), "1-4": ("046d", "c52b")})

    assert sysfs_has_device(0x1038, [0x12E0, 0x12E5], sys_root=root)
    assert not sysfs_has_device(0x1038, [0x2202], sys_root=root)
    assert not sysfs_has_device(0x1038, [0x12E0], sys_root=tmp_path / "missing")


def test_refresh_drops_pyusbs_cached_backend(monkeypatch):
    cached = MagicMock()
    monkeypatch.setattr(libusb1, "_lib_object", cached)

    assert refresh_libusb_context(logging.getLogger("test"))
    assert libusb1._lib_object is None


def test_nothing_to_refresh_before_the_first_backend(monkeypatch):
    monkeypatch.setattr(libusb1, "_lib_object", None)

    assert not refresh_libusb_context(logging.getLogger("test"))


def _engine():
    """A bare CoreEngine with only what the detection path reads."""
    import threading

    from arctis_sound_manager.core import CoreEngine

    engine = CoreEngine.__new__(CoreEngine)
    engine.logger = MagicMock()
    engine._device_lock = threading.RLock()
    engine._detect_lock = threading.Lock()
    engine._device_configured_event = threading.Event()
    engine._logged_no_device = False
    engine.usb_device = None
    engine.device_config = None
    cfg = MagicMock()
    cfg.vendor_id, cfg.product_ids = 0x1038, [0x12E0]
    engine.device_configurations = [cfg]
    engine._setup_generic_device = MagicMock(return_value=False)
    return engine


def test_detection_looks_again_with_a_fresh_context(monkeypatch):
    """First scan misses, the kernel lists the dongle: one refresh, then the
    second scan finds it and detection goes on."""
    from arctis_sound_manager import core

    engine = _engine()
    dongle = MagicMock()
    found = iter([None, dongle])
    monkeypatch.setattr(core.CoreEngine, "_find_hid_device", lambda self, v, p: next(found))
    monkeypatch.setattr(core, "sysfs_has_device", lambda v, p: True)
    refresh = MagicMock(return_value=True)
    monkeypatch.setattr(core, "refresh_libusb_context", refresh)
    # Stop right after detection: past it is device init, not under test.
    monkeypatch.setattr(core.CoreEngine, "teardown", MagicMock(side_effect=StopIteration))
    engine.device_config = MagicMock()  # a different config → teardown()

    try:
        core.CoreEngine.configure_virtual_sinks(engine)
    except StopIteration:
        pass

    refresh.assert_called_once()
    engine._setup_generic_device.assert_not_called()


def test_no_refresh_when_the_kernel_does_not_list_it_either(monkeypatch):
    from arctis_sound_manager import core

    engine = _engine()
    monkeypatch.setattr(core.CoreEngine, "_find_hid_device", lambda self, v, p: None)
    monkeypatch.setattr(core, "sysfs_has_device", lambda v, p: False)
    refresh = MagicMock(return_value=True)
    monkeypatch.setattr(core, "refresh_libusb_context", refresh)

    core.CoreEngine.configure_virtual_sinks(engine)

    refresh.assert_not_called()


def test_the_refresh_is_throttled(monkeypatch):
    """A device the kernel lists but libusb never reports must not rebuild
    the context on every 3-second rescan."""
    from arctis_sound_manager import core

    engine = _engine()
    monkeypatch.setattr(core.CoreEngine, "_find_hid_device", lambda self, v, p: None)
    monkeypatch.setattr(core, "sysfs_has_device", lambda v, p: True)
    refresh = MagicMock(return_value=True)
    monkeypatch.setattr(core, "refresh_libusb_context", refresh)

    for _ in range(5):
        core.CoreEngine.configure_virtual_sinks(engine)

    refresh.assert_called_once()
