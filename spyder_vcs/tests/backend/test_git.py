#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

# Standard library imports
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
import os.path as osp
from tempfile import TemporaryDirectory
import typing
import subprocess

# Third party imports
import pytest
from hypothesis import (strategies as st, given, assume, settings, Phase)

# Local imports
from spyder.utils import programs

from . import template
from .generation import FilesTreeGenerator

from ...utils.api import ChangedStatus, VCSBackendBase
from ...utils.backend import GitBackend
from ...utils.errors import VCSPropertyError, VCSFeatureError

git = programs.find_program("git")

pytestmark = [
    pytest.mark.skipif(
        git is None,
        reason="Git is required to run test on git backend",
    )
]


# --- Common functions and helpers ---
def _run_helper(program=programs.find_program("git"),
                args=(),
                cwd=None,
                env=None) -> typing.Tuple[int, bytes, bytes]:
    if program:
        try:
            proc = programs.run_program(program, args, cwd=cwd, env=env)
            output, err = proc.communicate()
            return proc.returncode, output, err

        except (subprocess.CalledProcessError, AttributeError, OSError):
            pass
    return None, None, None


def _create_test_commit(repodir: TemporaryDirectory):
    """Make a commit before any branch creation."""
    # open(osp.join(repodir.name, "test"), "w").write("test")
    subprocess.check_output([git, "add", "."], cwd=repodir.name)
    subprocess.check_output([git, "commit", "--allow-empty", "-am", "test"],
                            cwd=template.tempdir_tostr(repodir))


# --- Strategies and Hypothesis stuff ---
@st.composite
def remote_empty(draw: st.DataObject) -> TemporaryDirectory:
    """Create an empty git remote repository."""
    root = TemporaryDirectory()
    _run_helper(args=["init", "--bare"], cwd=root.name)
    return root


@st.composite
def local_empty(draw: st.DataObject) -> TemporaryDirectory:
    """Create an empty git local repository."""
    root = TemporaryDirectory()
    _run_helper(args=["init"], cwd=root.name)
    return root


@st.composite
def local_with_remote(draw: st.DataObject,
                      return_remote: bool = False) -> TemporaryDirectory:
    """Generate a local repository with a remote associated."""
    local = draw(local_empty())
    remote = draw(remote_empty())
    _run_helper(args=["remote", "add", "origin", remote.name], cwd=local.name)
    if return_remote:
        return local, remote
    return local


BRANCHNAME = st.from_regex(
    r"^[\w\d\-\.]+$",
    fullmatch=True,
).map(lambda x: x.strip("-. ")).filter(lambda x: x and ".." not in x)

BRANCHES = st.lists(
    BRANCHNAME,
    unique=True,
    min_size=1,
    max_size=6,
)

BASE_SETTINGS = settings(template.BASE_SETTINGS, max_examples=25)


# --- Tests ---
class TestGit(template.HyTemplateCreate, template.TemplateStatus,
              template.TemplateBranches, template.TemplateStage):
    """
    **Untested cases**

    - TemplateBranches: test non-editable branches.
    """

    backend: typing.Type[VCSBackendBase] = GitBackend

    local_repository = local_empty()
    remote_repository = remote_empty()
    local_with_remote_repository = local_with_remote(return_remote=True)

    def _create_branch(self, repodir: TemporaryDirectory, branchname: str):
        subprocess.check_output([git, "branch", branchname], cwd=repodir.name)

    @template.feature_mark(backend, ("branch", "fget"))
    @BASE_SETTINGS
    @given(st.one_of(local_empty(), local_with_remote()), BRANCHES,
           st.integers(0, 5))
    def test_branch_getter(self, repodir: TemporaryDirectory, branches: list,
                           index: int):
        _create_test_commit(repodir)

        index = index % len(branches)
        inst = self.backend(repodir.name)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        subprocess.check_output([git, "checkout", branches[index]],
                                cwd=repodir.name)

        assert branches[index] == inst.branch

    @template.feature_mark(backend, "change")
    @BASE_SETTINGS
    @given(local_empty(), st.data())
    # --- test_change ---
    def test_change(self, repodir: TemporaryDirectory, data: st.DataObject):
        inst = self.backend(repodir.name)
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            subprocess.check_output([git, "add", "."], cwd=repodir.name)
            changes = data.draw(generator.change_tree(files,
                                                      only_changes=True))

        for relpath, (change_status, _) in changes.items():
            change = inst.change(relpath, prefer_unstaged=True)
            assert (change and not change.get("staged")
                    and change.get("kind") == change_status)

    @template.feature_mark(backend, ("changes", "fget"))
    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_changes_getter(self, repodir: str, data: st.DataObject):
        inst = self.backend(repodir.name)
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            subprocess.check_output([git, "add", "."], cwd=repodir.name)

            changes = data.draw(
                generator.change_tree(
                    files,
                    only_changes=True,
                ))
        git_changes = inst.changes

        unstaged_count = 0
        for change in git_changes:
            kind = change.get("kind")
            path = osp.normpath(change.get("path"))
            staged = change.get("staged")
            assert kind and path and staged is not None

            if staged:
                assert kind == ChangedStatus.ADDED and path in files
            else:
                unstaged_count += 1
                assert kind == changes[path][0]

        assert unstaged_count == len(changes)

    @template.feature_mark(backend, ("branch", "fset"))
    @template.feature_mark(backend, ("branch", "fget"))
    @BASE_SETTINGS
    @given(local_empty(), BRANCHES, st.integers(0, 5))
    def test_branch_setter_good(self, repodir, branches, index):
        _create_test_commit(repodir)

        index = index % len(branches)
        inst = self.backend(repodir.name)
        branchname = branches[index]

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        inst.branch = branchname

        assert inst.branch == branchname

    @template.feature_mark(backend, ("branch", "fset"))
    @BASE_SETTINGS
    @given(local_empty(), BRANCHNAME, BRANCHES)
    def test_branch_setter_nonexisting(self, repodir, branchname, branches):
        assume(branchname not in branches)

        _create_test_commit(repodir)
        inst = self.backend(repodir.name)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        try:
            inst.branch = branchname
        except VCSPropertyError as ex:
            assert ex.name == "branch" and ex.operation == "set"
        else:
            assert False, "branch.fset should raise a VCSPropertyError"

    @template.feature_mark(backend, ("branches", "fget"))
    @BASE_SETTINGS
    @given(local_empty(), BRANCHES)
    def test_branches_getter(self, repodir, branches):
        _create_test_commit(repodir)
        inst = self.backend(repodir.name)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        assert frozenset(branches) <= frozenset(inst.branches)

    @template.feature_mark(backend, ("editable_branches", "fget"))
    @BASE_SETTINGS
    @given(local_empty(), BRANCHES)
    def test_editable_branches_getter(self, repodir, branches):
        _create_test_commit(repodir)

        inst = self.backend(repodir.name)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)
        assert frozenset(branches) <= frozenset(inst.editable_branches)

    @template.feature_mark(backend, "create_branch")
    @template.feature_mark(backend, ("editable_branches", "fget"))
    @settings(BASE_SETTINGS, deadline=1500)
    @given(local_empty(), BRANCHES, st.integers(0, 5), st.booleans())
    def test_create_branch_good(self, repodir, branches, index, empty):
        _create_test_commit(repodir)

        index = index % len(branches)
        inst = self.backend(repodir.name)
        branchname = branches.pop(index)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        assert inst.create_branch(branchname, empty=empty)

        assert branchname == inst.branch
        if not empty:
            # Unless a commit is done in the repository,
            # git does not shows it in git branch
            # because git create the HEAD on first commit.
            assert branchname in inst.editable_branches

    @template.feature_mark(backend, "create_branch")
    @settings(BASE_SETTINGS, max_examples=2)
    @given(local_empty(), BRANCHES, st.integers(0, 5), st.booleans())
    def test_create_branch_existing(self, repodir, branches, index, empty):
        _create_test_commit(repodir)

        index = index % len(branches)
        inst = self.backend(repodir.name)
        branchname = branches[index]

        with ThreadPoolExecutor() as pool:
            pool.map(partial(self._create_branch, repodir), branches)

        try:
            inst.create_branch(branchname, empty=empty)
        except VCSFeatureError as ex:
            assert ex.feature.__name__ == "create_branch"
        else:
            assert False, "create_branch should raise a VCSFeatureError"

    @BASE_SETTINGS
    @given(local_empty(), BRANCHES.filter(lambda x: len(x) > 1), st.data())
    def test_delete_branch_good(self, repodir, branches, data):
        _create_test_commit(repodir)
        super().test_delete_branch_good(
            repodir.name,
            data.draw(st.sampled_from(branches)),
            branches,
        )

    @BASE_SETTINGS
    @given(local_empty(), BRANCHES.filter(lambda x: len(x) > 1), BRANCHNAME)
    def test_delete_branch_nonexistsing(self, repodir, branches, branchname):
        assume(branchname not in branches)
        _create_test_commit(repodir)
        super().test_delete_branch_nonexistsing(repodir, branchname, branches)

    @BASE_SETTINGS
    @given(local_empty(), BRANCHES.filter(lambda x: len(x) > 1), st.data())
    def test_delete_branch_is_current(self, repodir, branches, data):
        _create_test_commit(repodir)
        super().test_delete_branch_is_current(
            repodir, data.draw(st.sampled_from(branches)), branches)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_stage_good(self, repodir, data):
        generator = FilesTreeGenerator(repodir.name)
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            _create_test_commit(repodir)
            changes = data.draw(
                generator.change_tree(
                    files,
                    only_changes=True,
                ))

        for file in changes:
            super().test_stage_good(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_stage_already_staged(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            _create_test_commit(repodir)
            changes = data.draw(
                generator.change_tree(files, only_changes=True).filter(bool))

            subprocess.check_output([git, "add", "."], cwd=repodir.name)

        for file in changes:
            super().test_stage_already_staged(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_stage_not_changed(self, repodir, data):
        # Slow (> 500 ms max)
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

        _create_test_commit(repodir)

        for file in files:
            super().test_stage_not_changed(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_stage_all(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            _create_test_commit(repodir)
            files = data.draw(generator.change_tree(files))
            subprocess.check_output([git, "add", "."], cwd=repodir.name)
            data.draw(
                generator.change_tree(
                    files,
                    only_changes=True,
                ).filter(bool))
        super().test_stage_all(repodir)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    # Slow (> 500 ms max)
    def test_unstage_good(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())
            _create_test_commit(repodir)
            changes = data.draw(generator.change_tree(files,
                                                      only_changes=True))

        subprocess.check_output([git, "add", "."], cwd=repodir.name)
        for file in changes:
            super().test_unstage_good(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_unstage_already_unstaged(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())
            _create_test_commit(repodir)
            changes = data.draw(generator.change_tree(files,
                                                      only_changes=True))

        for file in changes:
            super().test_unstage_already_unstaged(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    # Slow (> 500 ms max)
    def test_unstage_not_changed(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

        _create_test_commit(repodir)
        for file in files:
            super().test_unstage_not_changed(repodir, file)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_unstage_all(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())

            _create_test_commit(repodir)
            files = data.draw(generator.change_tree(files))
            subprocess.check_output([git, "add", "."], cwd=repodir.name)
            data.draw(
                generator.change_tree(
                    files,
                    only_changes=True,
                ).filter(bool))
        super().test_unstage_all(repodir)

    @BASE_SETTINGS
    @given(local_empty(), st.data())
    def test_undo_stage(self, repodir, data):
        with FilesTreeGenerator(repodir.name) as generator:
            files = data.draw(generator.create_tree())
            # _create_test_commit(repodir)
            # changes = data.draw(generator.change_tree(files,
            #                                           only_changes=True))

        subprocess.check_output([git, "add", "."], cwd=repodir.name)
        for file in files:
            super().test_undo_stage(repodir, file)
