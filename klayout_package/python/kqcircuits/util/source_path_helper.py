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

"""Helpers for resolving source roots and module paths for KQCircuits packages."""

import os
import sys
from pathlib import Path


def get_source_paths(primary_source_path, raw_value=None):
    """Collect all configured source roots in precedence order."""
    primary_source_path = Path(primary_source_path).resolve()
    source_paths = [primary_source_path]

    for candidate in get_extra_source_paths(raw_value):
        if candidate not in source_paths:
            source_paths.append(candidate)

    for candidate in get_scdevice_source_paths(primary_source_path):
        if candidate not in source_paths:
            source_paths.append(candidate)

    return source_paths


def get_extra_source_paths(raw_value=None):
    """Parse extra source roots from ``KQC_EXTRA_SRC_PATHS`` style values."""
    if raw_value is None:
        raw_value = os.getenv("KQC_EXTRA_SRC_PATHS", "")

    source_paths = []
    for raw_path in raw_value.split(os.pathsep):
        raw_path = raw_path.strip()
        if not raw_path:
            continue
        source_path = Path(raw_path).expanduser().resolve()
        if source_path.is_dir() and source_path not in source_paths:
            source_paths.append(source_path)

    return source_paths


def get_scdevice_source_paths(primary_source_path):
    """Auto-discover sibling source roots for the SCDevice umbrella layout."""
    primary_source_path = Path(primary_source_path).resolve()
    if len(primary_source_path.parts) < 4:
        return []

    if not (
        primary_source_path.name == "kqcircuits"
        and primary_source_path.parent.name == "python"
        and primary_source_path.parent.parent.name == "klayout_package"
        and primary_source_path.parent.parent.parent.name == "KQCircuits"
    ):
        return []

    scdevice_root = primary_source_path.parent.parent.parent.parent
    scdevice_source_root = (scdevice_root / "scdevice_pcells").resolve()
    if scdevice_source_root.is_dir():
        return [scdevice_source_root]

    return []


def ensure_source_path_parents_on_sys_path(source_paths):
    """Ensure the parent directory of each source root is importable."""
    for source_path in source_paths:
        parent = str(Path(source_path).resolve().parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)


def resolve_module_path(path_value, source_paths):
    """Resolve a source file or package-relative path into a Python module path."""
    candidate = Path(path_value).expanduser()
    candidate_without_suffix = candidate.with_suffix("") if candidate.suffix == ".py" else candidate
    resolved_source_paths = [Path(source_path).resolve() for source_path in source_paths]

    if candidate_without_suffix.is_absolute():
        resolved_candidate = candidate_without_suffix.resolve()
        for source_path in resolved_source_paths:
            source_parent = source_path.parent
            try:
                return ".".join(resolved_candidate.relative_to(source_parent).parts)
            except ValueError:
                continue
    else:
        parts = candidate_without_suffix.parts
        for source_path in resolved_source_paths:
            package_name = source_path.name
            for idx, part in enumerate(parts):
                if part == package_name:
                    return ".".join(parts[idx:])

    available_roots = ", ".join(str(path) for path in resolved_source_paths)
    raise ValueError(f"Could not resolve '{path_value}' under configured source roots: {available_roots}")
