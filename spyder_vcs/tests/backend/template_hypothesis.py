#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
A set of Hypothesis powered templates for testing backends.

All the templates here acts as mixins, rather than
"""

# Standard library imports
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
import typing

# Third party imports
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

# Local imports
from .generation import FilesTreeGenerator
from .template import TemplateBasic, TemplateCreate, tempdir_tostr

__all__ = ("BASE_SETTINGS", "HyTemplateBasic", "HyTemplateCreate")

TEMPDIR = typing.Union[TemporaryDirectory, str]

BASE_SETTINGS = settings(
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.data_too_large),
    deadline=1000,
)


class HyTemplateBasic(TemplateBasic):
    """
    The base of all Hypothesis powered backend test templates.

    In addition to TemplateBasic requirements, any subclass of this must
    provide the following strategies: local_repository, remote_repository,
    local_with_remote_repository.
    """

    local_repository: st.SearchStrategy[TEMPDIR]
    remote_repository: st.SearchStrategy[TEMPDIR]
    local_with_remote_repository: st.SearchStrategy[typing.Tuple[TEMPDIR,
                                                                 TEMPDIR]]

    def _draw_repodir(
        self,
        data: st.DataObject,
        attrs: typing.Iterable[str] = ("local_repository", )
    ) -> typing.Tuple[TEMPDIR, typing.Union[TEMPDIR, typing.Sequence[TEMPDIR]]]:
        drawed_repo = data.draw(st.one_of(*(getattr(self, attr) for attr in attrs)))

        if isinstance(drawed_repo, Iterable):
            return drawed_repo, tuple(tempdir_tostr(x) for x in drawed_repo)
        return drawed_repo, tempdir_tostr(drawed_repo)

    @given(st.data())
    # @settings(max_examples=2)
    def test_init_good(self, data: st.DataObject):
        _, repodir = self._draw_repodir(
            data, ("local_repository", "local_with_remote_repository"))
        if not isinstance(repodir, str):
            repodir = repodir[0]
        super().test_init_good(repodir)

    @given(st.builds(TemporaryDirectory))
    # @settings(max_examples=1)
    def test_init_norepo(self, norepodir: TemporaryDirectory):
        super().test_init_norepo(norepodir.name)


class HyTemplateCreate(HyTemplateBasic, TemplateCreate):
    """Hypothesis powered implementations of TemplateCreate."""
    @BASE_SETTINGS
    # @settings(max_examples=1)
    @given(st.builds(TemporaryDirectory))
    def test_create_empty(self, repodir):
        super().test_create_empty(repodir.name)

    @BASE_SETTINGS
    # @settings(max_examples=1)
    @given(st.builds(TemporaryDirectory), st.data())
    def test_create_noauth(self, repodir: TemporaryDirectory,
                           data: st.DataObject):
        _, from_ = self._draw_repodir(data, ("remote_repository", ))
        super().test_create_noauth(repodir.name, Path(from_).as_uri())
