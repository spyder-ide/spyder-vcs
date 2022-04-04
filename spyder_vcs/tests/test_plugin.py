#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Tests for VCS the plugin."""

# Third party imports
import pytest


@pytest.fixture
def setup_vcs(qtbot):
    """Set up the VCS plugin."""
    from ..plugin import VCS
    vcs = VCS(None)
    qtbot.addWidget(vcs)
    vcs.show()
    return vcs


@pytest.mark.skip()
def test_basic_initialization(setup_vcs):
    """Test VCS initialization."""
    # Assert that plugin object exist
    assert setup_vcs is not None


if __name__ == "__main__":
    pytest.main()
