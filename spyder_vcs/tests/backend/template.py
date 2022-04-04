#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""A set of templates for testing backends."""

import typing
import os.path as osp
import functools
from tempfile import TemporaryDirectory
from functools import partial
# Standard library imports
from concurrent.futures.thread import ThreadPoolExecutor

# Third party imports
import pytest

# Local imports
from ...utils.api import ChangedStatus, VCSBackendBase
from ...utils.errors import VCSBackendFail

__all__ = [
    "TemplateBasic", "TemplateCreate", "TemplateStatus", "TemplateStage",
    "feature_mark", "feature_checker", "tempdir_tostr"
]

TEMPDIR = typing.Union[TemporaryDirectory, str]


def tempdir_tostr(tempdir: TEMPDIR) -> str:
    """Convert a TemporaryDirectory object to a str."""
    if isinstance(tempdir, TemporaryDirectory):
        return tempdir.name
    return tempdir


def feature_mark(
        backend: VCSBackendBase,
        featurename: typing.Union[typing.Tuple[str, str], str]) -> pytest.mark:
    """
    A Pytest mark for features.

    Parameters
    ----------
    backend : VCSBackendBase
        The backend where features are stored.
    featurename : str or tuple of str
        The feature name.
        If the feature is contained in a property,
        a tuple of 2 str must be provided.

    Returns
    -------
    pytest.mark
        The mark (skipif).
    """
    if isinstance(featurename, str):
        feature = getattr(backend, featurename)
    else:
        feature = getattr(getattr(backend, featurename[0]), featurename[1])

    return pytest.mark.skipif(
        not feature.enabled,
        reason="{} not implemented in {}".format(
            feature,
            backend.__name__,
        ),
    )


def feature_checker(
    *features: typing.Union[str, typing.Tuple[str, str]]
) -> typing.Callable[..., object]:
    """
    A checker decorator for given features.

    Unlike feature_mark, the check is done on test execution.

    Parameters
    ----------
    features : str or tuple of str
        The feature names.

        If the feature is contained in a property,
        a tuple of 2 str must be provided.
    """
    def _decorator(
            func: typing.Callable[..., None]) -> typing.Callable[..., None]:
        @functools.wraps(func)
        def _wrapper(self, *args, **kwargs) -> object:
            backend = self.backend
            for featurename in features:
                if isinstance(featurename, str):
                    feature = getattr(backend, featurename)
                else:
                    feature = getattr(getattr(backend, featurename[0]),
                                      featurename[1])

                if not feature.enabled:
                    pytest.skip("{} not implemented in {}".format(
                        featurename if isinstance(featurename, str) else
                        "{}.{}".join(featurename),
                        backend.__name__,
                    ))
                    return None

            return func(self, *args, **kwargs)

        return _wrapper

    return _decorator


class TemplateBasic(object):
    """
    The base of all backend test templates.

    .. tip::
        All the test signatures are not mandatory,
        and can be changed if needed.

    .. note::
        The `repodir` parameter, if not specified, always refers
        to the repository directory.
    """

    backend: typing.Type[VCSBackendBase] = None
    """The backend to test. Must be set by subclass."""
    def test_init_good(self, repodir: TEMPDIR):
        """
        Test backend initialization.

        This test has a generic implementation.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert isinstance(inst, self.backend)

    def test_init_norepo(self, norepodir: TEMPDIR):
        """
        Test backend initialization fail when directory is not a valid repo.

        This test has a generic implementation.
        """
        norepodir = tempdir_tostr(norepodir)
        try:
            self.backend(norepodir)
        except VCSBackendFail as ex:
            assert ex.directory == norepodir
            assert ex.backend_type == self.backend
            assert not ex.is_valid_repository
        else:
            assert False, "The backend must raise a VCSBackendFail."


class TemplateCreate(TemplateBasic):
    """Some tests for create group."""
    @feature_checker("create")
    def test_create_empty(self, repodir: TEMPDIR):
        """
        Test create method with from_ == None.

        This test has a generic implementation.

        Parameters
        ----------
        repodir : str
            The new repo directory.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend.create(repodir)
        assert isinstance(inst, self.backend)
        assert inst.repodir == repodir
        assert osp.exists(repodir)

    @feature_checker("create")
    def test_create_noauth(self, repodir: TEMPDIR, from_: str):
        """
        Test create method with from_ != None.

        This test has a generic implementation.

        Parameters
        ----------
        repodir : str
            The new repo directory.
        from : str
            The remote repo url.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend.create(repodir, from_=from_)
        assert isinstance(inst, self.backend)
        assert inst.repodir == repodir
        assert osp.exists(repodir)


class TemplateStatus(TemplateBasic):
    """Some tests for status group."""
    def test_branch_getter(self, repodir: TEMPDIR):
        """
        Check if the current branch returned is correct.

        This test is not implemented.
        """
        raise NotImplementedError()

    def test_change(self, repodir: TEMPDIR, path: str):
        """
        Check if the change in given path is correct.

        This test is not implemented.

        Parameters
        ----------
        path : str
            The path to check.
        """
        raise NotImplementedError()

    def test_changes_getter(self, repodir: TEMPDIR):
        """
        Check if reposiory changes are correct.

        This test is not implemented.
        """
        raise NotImplementedError()


class TemplateBranches(TemplateBasic):
    """Some tests for branch group."""
    def test_branch_getter(self, repodir: TEMPDIR):
        """
        Check if the current branch returned is correct.

        This test is not implemented.
        """
        raise NotImplementedError()

    def test_branch_setter_good(self, repodir: TEMPDIR, branchname: str):
        """
        Check if changing branch works as expected.

        This test is not implemented.

        Parameters
        ----------
        branchname : str
            The branch to change.
        """
        raise NotImplementedError()

    def test_branch_setter_nonexisting(self, repodir: TEMPDIR,
                                       branchname: str):
        """
        Check if changing branch to an invalid branch raises an error.

        This test is not implemented.

        Parameters
        ----------
        branchname : str
            The invalid branch to change.
        """
        raise NotImplementedError()

    def test_branches_getter(self, repodir: TEMPDIR):
        """
        Check if repository branches are correct.

        This test is not implemented.
        """
        raise NotImplementedError()

    def test_editable_branches_getter(self, repodir: TEMPDIR):
        """
        Check if repository edtiable branches are correct.

        This test is not implemented.
        """
        raise NotImplementedError()

    def test_create_branch_good(self, repodir: TEMPDIR, branchname: str,
                                empty: bool):
        """
        Check if branch creation is done correcly.

        This test is not implemented.

        Parameters
        ----------
        branchname : str
            The branch to create.
        empty : bool
            See :meth:`.VCSBackendBase.create_branch`.
        """
        raise NotImplementedError()

    def test_create_branch_existing(self, repodir: TEMPDIR, branchname: str,
                                    empty: bool):
        """
        Check if branch creation fails when branch already exists.

        This test is not implemented.

        Parameters
        ----------
        branchname : str
            The branch to create.
        empty : bool
            See :meth:`.VCSBackendBase.create_branch`.
        """
        raise NotImplementedError()

    @feature_checker("delete_branch", "create_branch", ("branch", "fset"),
                     ("branches", "fget"))
    def test_delete_branch_good(
            self,
            repodir: TEMPDIR,
            branchname: str,
            branches: typing.Iterable[str] = (),
    ):
        """
        Check if branch deletion is done correcly.

        This test has a generic implementation.

        Parameters
        ----------
        branchname : str
            The branch to delete.

        branches : iterable of str, optional
            A list of branches to create.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(inst.create_branch), branches)

        if inst.branch == branchname:
            # skip test
            return

        assert inst.delete_branch(branchname)
        assert branchname not in inst.branches

    @feature_checker("delete_branch", "create_branch", ("branches", "fget"))
    def test_delete_branch_nonexistsing(
            self,
            repodir: TEMPDIR,
            branchname: str,
            branches: typing.Iterable[str] = (),
    ):
        """
        Check if branch deletion fails when branch not exists.

        This test has a generic implementation.

        Parameters
        ----------
        branchname : str
            The branch to delete.
        branches : iterable of str, optional
            A list of branches to create.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(inst.create_branch), branches)

        if branchname in inst.branches:
            # Skip test
            return

        assert not inst.delete_branch(branchname)

    @feature_checker("delete_branch", "create_branch", ("branch", "fset"),
                     ("branches", "fget"))
    def test_delete_branch_is_current(
            self,
            repodir: TEMPDIR,
            branchname: str,
            branches: typing.Iterable[str] = (),
    ):
        """
        Check if branch deletion fails when the branch is the current one.

        This test has a generic implementation.

        Parameters
        ----------
        branchname : str
            The branch name to delete.
        branches : iterable of str, optional
            A list of branches to create.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)

        with ThreadPoolExecutor() as pool:
            pool.map(partial(inst.create_branch), branches)

        inst.branch = branchname

        assert not inst.delete_branch(branchname)


class TemplateStage(TemplateBasic):
    """
    Some tests for stage-unstage group.

    Default implementations are incomplete and requires
    that change and changes features are working in the backend
    with the staged field supported.
    """

    # Stage tests
    @feature_checker("change", "stage")
    def test_stage_good(self, repodir: TEMPDIR, path: str):
        """
        Stage a path, then check if it really staged.

        Parameters
        ----------
        path : str
            The path to stage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert inst.stage(path)
        change = inst.change(path, prefer_unstaged=True)
        assert change and change.get("staged") is True

    @feature_checker("change", "stage")
    def test_stage_already_staged(self, repodir: TEMPDIR, path: str):
        """
        Stage a path that is already staged.

        Parameters
        ----------
        path : str
            The path to stage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        change = inst.change(path)
        assert change and change.get("staged") is True
        assert inst.stage(path)
        new_change = inst.change(path, prefer_unstaged=True)
        assert change == new_change

    @feature_checker("stage")
    def test_stage_not_changed(self, repodir: TEMPDIR, path: str):
        """
        Stage a path that is not changed.

        Parameters
        ----------
        path : str
            The path to stage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert not inst.stage(path)

    @feature_checker(("changes", "fget"), "stage_all")
    def test_stage_all(self, repodir: TEMPDIR):
        """
        Stage all changes, then check if there are
        no unstaged changes left.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert inst.stage_all()
        for change in inst.changes:
            assert change.get("staged") is True

    # Unstage tests
    @feature_checker("change", "unstage")
    def test_unstage_good(self, repodir: TEMPDIR, path: str):
        """
        Unstage a path, then check if it really unstaged.

        Parameters
        ----------
        path : str
            The path to unstage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert inst.unstage(path)
        change = inst.change(path)
        assert change and change.get("staged") is False

    @feature_checker("change", "unstage")
    def test_unstage_already_unstaged(self, repodir: TEMPDIR, path: str):
        """
        Unstage a path that is already unstaged.

        Parameters
        ----------
        path : str
            The path to unstage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        change = inst.change(path, prefer_unstaged=True)
        assert change and change.get("staged") is False
        assert inst.unstage(path)
        new_change = inst.change(path)
        assert change == new_change

    @feature_checker("change", "unstage")
    def test_unstage_not_changed(self, repodir: TEMPDIR, path: str):
        """
        Untage a path that is not changed.

        Parameters
        ----------
        path : str
            The path to unstage.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert not inst.unstage(path)

    @feature_checker(("changes", "fget"), "unstage_all")
    def test_unstage_all(self, repodir: TEMPDIR):
        """
        Unstage all changes, then check if there are
        no staged changes left.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        assert inst.unstage_all()
        for change in inst.changes:
            assert change.get("staged") is False


class TemplateCommit(TemplateBasic):
    """Some tests for commit group."""
    @feature_checker("commit", ("changes", "fget"))
    def test_commit_good(self, repodir: TEMPDIR, message: str):
        """
        Test commit creation without history check.

        It has a partial implementation, that requires
        at least one change that allows commit
        (e.g. if VCS has the staged area,
        at least one staged change should exists).
        A generic check is done in the test body.

        Parameters
        ----------
        message : str
            A valid commit message.
        """
        repodir = tempdir_tostr(repodir)
        inst = self.backend(repodir)
        changes = tuple(
            filter(
                lambda x: x.get("kind", ChangedStatus.UNCHANGED) not in
                (ChangedStatus.UNCHANGED, ChangedStatus.UNKNOWN), inst.change))

        assert changes, "There should be at least one valid change."
        if "staged" in inst.changes.extra["states"]:
            for change in changes:
                if changes[0].get("staged"):
                    break
            else:
                assert False, ("If changes supports the staged key,"
                               "there should be at least one staged change.")

            assert changes[0].get("staged")

        assert inst.commit(message)


try:
    from .template_hypothesis import *
except ImportError as ex:
    print(repr(ex))
else:
    from .template_hypothesis import __all__ as _hy_all
    __all__.extend(_hy_all)
