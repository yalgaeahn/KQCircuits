# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import os
from pathlib import Path

from kqcircuits.util.source_path_helper import get_extra_source_paths, resolve_module_path


def test_get_extra_source_paths_returns_empty_without_environment(monkeypatch):
    monkeypatch.delenv("KQC_EXTRA_SRC_PATHS", raising=False)
    assert get_extra_source_paths() == []


def test_get_extra_source_paths_parses_multiple_directories(monkeypatch, tmp_path):
    first = tmp_path / "scdevice_pcells"
    second = tmp_path / "more_pcells"
    first.mkdir()
    second.mkdir()

    monkeypatch.setenv("KQC_EXTRA_SRC_PATHS", os.pathsep.join((str(first), str(second))))

    assert get_extra_source_paths() == [first.resolve(), second.resolve()]


def test_resolve_module_path_accepts_registered_relative_paths():
    source_paths = [
        Path("/tmp/kqcircuits"),
        Path("/tmp/scdevice_pcells"),
    ]

    assert resolve_module_path("kqcircuits/chips/demo.py", source_paths) == "kqcircuits.chips.demo"
    assert resolve_module_path("scdevice_pcells/chips/sqnl_launchers.py", source_paths) == (
        "scdevice_pcells.chips.sqnl_launchers"
    )


def test_resolve_module_path_accepts_absolute_paths(tmp_path):
    package_root = tmp_path / "scdevice_pcells"
    module_path = package_root / "qubits" / "double_pads_sqnl.py"
    module_path.parent.mkdir(parents=True)
    module_path.touch()

    assert resolve_module_path(str(module_path), [package_root]) == "scdevice_pcells.qubits.double_pads_sqnl"
