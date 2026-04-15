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


import logging
import importlib
import sys
from pathlib import Path

from kqcircuits.pya_resolver import pya
import kqcircuits.defaults as defaults
import kqcircuits.util.library_helper as library_helper

from kqcircuits.util.library_helper import load_libraries, delete_library, delete_all_libraries

log = logging.getLogger(__name__)


# normal cases


def test_load():
    libraries = load_libraries(path="elements")
    pcells = [name for library in libraries.values() for name in library.layout().pcell_names()]
    assert "Airbridge Rectangular" in pcells


def test_load_with_flush(caplog):
    level = logging.root.level
    caplog.set_level(logging.DEBUG)
    libraries = load_libraries(flush=True, path="elements")
    pcells = [name for library in libraries.values() for name in library.layout().pcell_names()]
    assert "Airbridge Rectangular" in pcells
    assert "Deleted all libraries." in caplog.text
    assert "Reloaded module 'airbridge_rectangular'." in caplog.text
    caplog.set_level(level)


def test_load_all():
    result = load_libraries()
    assert len(result) >= 4
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" in pya.Library.library_names()
    assert "Test Structure Library" in pya.Library.library_names()
    assert "Junction Library" in pya.Library.library_names()


def test_delete_all():
    load_libraries()
    assert len(pya.Library.library_names()) > 1
    delete_all_libraries()
    assert pya.Library.library_names() == ["Basic"]


def test_delete():
    delete_library("Chip Library")
    load_libraries(path="elements")
    assert "Element Library" in pya.Library.library_names()
    assert "Chip Library" not in pya.Library.library_names()
    delete_library("Element Library")
    assert "Element Library" not in pya.Library.library_names()


# edge cases


def test_without_input():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library()
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_none():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library(None)
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_invalid_name():
    load_libraries()
    before_count = len(pya.Library.library_names())
    delete_library("foo")
    after_count = len(pya.Library.library_names())
    assert before_count == after_count


def test_load_all_with_external_source_root(monkeypatch, tmp_path):
    package_root = _create_external_package(tmp_path)
    monkeypatch.setenv("KQC_EXTRA_SRC_PATHS", str(package_root))

    try:
        importlib.reload(defaults)
        importlib.reload(library_helper)
        library_helper.load_libraries(flush=True)
        chip_pcells = library_helper.load_libraries()["Chip Library"].layout().pcell_names()
        qubit_pcells = library_helper.load_libraries()["Qubit Library"].layout().pcell_names()

        assert package_root in defaults.SRC_PATHS
        assert str(package_root.parent) in sys.path
        assert "Sqnl Launchers" in chip_pcells
        assert "Double Pads SQNL" in qubit_pcells
    finally:
        library_helper.delete_all_libraries()
        monkeypatch.delenv("KQC_EXTRA_SRC_PATHS", raising=False)
        importlib.reload(defaults)
        importlib.reload(library_helper)


def _create_external_package(tmp_path):
    package_root = tmp_path / "scdevice_pcells"
    _write_file(
        package_root / "__init__.py",
        '"""Temporary external PCells package for tests."""\n',
    )
    _write_file(package_root / "chips" / "__init__.py", "")
    _write_file(
        package_root / "chips" / "sqnl_launchers.py",
        """
from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_sampleholders
from kqcircuits.util.parameters import Param, pdt

sampleholder_type_choices = list(default_sampleholders.keys())


class SqnlLaunchers(Chip):
    sampleholder_type = Param(pdt.TypeString, "Type of the launchers", "SMA8", choices=sampleholder_type_choices)

    def build(self):
        self.name_mask = "M001"
        self.name_chip = "BASIC"
        self.name_copy = "KAIST"
        self.name_brand = "SQNL"
        self.produce_launchers(self.sampleholder_type)
""".lstrip(),
    )
    _write_file(package_root / "qubits" / "__init__.py", "")
    _write_file(
        package_root / "qubits" / "double_pads_sqnl.py",
        """
from kqcircuits.util.geometry_helper import bspline_points
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.qubits.double_pads import DoublePads
from kqcircuits.pya_resolver import pya


@add_parameters_from(DoublePads, junction_type="Manhattan Single Junction")
class DoublePadsSQNL(DoublePads):
    island_spline = Param(
        pdt.TypeList,
        "Control points of a B-Spline that defines left half of the island",
        [-250, 20, -250, 80, -100, 100, 0, 100],
    )
    island_spline_samples = Param(
        pdt.TypeInt,
        "Number of samples taken from each island spline",
        100,
        docstring=(
            "Number of samples taken from each island spline. "
            "There is a spline for each consequent series of four control points"
        ),
    )

    def _build_island1(self, squid_height, taper_height):
        island1_bottom = self.squid_offset + squid_height / 2
        curve_start = pya.DPoint(0, island1_bottom + taper_height)
        island1_control_points = [curve_start + pya.DPoint(-self.island1_taper_width / 2, 0)] + [
            curve_start + pya.DPoint(float(self.island_spline[idx]), float(self.island_spline[idx + 1]))
            for idx in range(0, len(self.island_spline), 2)
        ]
        island1_control_points += [pya.DPoint(-p.x, p.y) for p in reversed(island1_control_points[:-1])]
        island1_polygon = pya.DPolygon(
            bspline_points(island1_control_points, self.island_spline_samples, startpoint=True, endpoint=True)
        )
        island1_region = pya.Region(island1_polygon.to_itype(self.layout.dbu))
        island1_taper = pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(self.island1_taper_width / 2, island1_bottom + taper_height + 1),
                    pya.DPoint(self.island1_taper_width / 2, island1_bottom + taper_height),
                    pya.DPoint(self.island1_taper_junction_width / 2, island1_bottom),
                    pya.DPoint(-self.island1_taper_junction_width / 2, island1_bottom),
                    pya.DPoint(-self.island1_taper_width / 2, island1_bottom + taper_height),
                    pya.DPoint(-self.island1_taper_width / 2, island1_bottom + taper_height + 1),
                ]
            ).to_itype(self.layout.dbu)
        )
        return island1_region + island1_taper

    def _build_island2(self, squid_height, taper_height):
        island2_top = self.squid_offset - squid_height / 2
        curve_start = pya.DPoint(0, island2_top - taper_height)
        island2_control_points = [curve_start + pya.DPoint(-self.island2_taper_width / 2, 0)] + [
            curve_start + pya.DPoint(float(self.island_spline[idx]), -float(self.island_spline[idx + 1]))
            for idx in range(0, len(self.island_spline), 2)
        ]
        island2_control_points += [pya.DPoint(-p.x, p.y) for p in reversed(island2_control_points[:-1])]
        island2_polygon = pya.DPolygon(
            bspline_points(island2_control_points, self.island_spline_samples, startpoint=True, endpoint=True)
        )
        island2_region = pya.Region(island2_polygon.to_itype(self.layout.dbu))
        island2_taper = pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(self.island2_taper_width / 2, island2_top - taper_height - 1),
                    pya.DPoint(self.island2_taper_width / 2, island2_top - taper_height),
                    pya.DPoint(self.island2_taper_junction_width / 2, island2_top),
                    pya.DPoint(-self.island2_taper_junction_width / 2, island2_top),
                    pya.DPoint(-self.island2_taper_width / 2, island2_top - taper_height),
                    pya.DPoint(-self.island2_taper_width / 2, island2_top - taper_height - 1),
                ]
            ).to_itype(self.layout.dbu)
        )
        return island2_region + island2_taper
""".lstrip(),
    )

    return package_root.resolve()


def _write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
