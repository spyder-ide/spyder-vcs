#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

# Standard library imports
from contextlib import suppress
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _TimeoutError
from pathlib import Path
import os
import os.path as osp
from tempfile import TemporaryDirectory
import typing
import platform
import shutil

# Third party imports
from hypothesis import strategies as st

# Local imports
from ...utils.api import ChangedStatus

# typing stuff
STR_OR_TEMP = typing.Union[str, TemporaryDirectory]

FILES = typing.Mapping[str, bytes]
FILE_CHANGES = typing.Mapping[str, typing.Tuple[int, typing.Union[str, None]]]

__all__ = ("FILENAME", "FilesTreeGenerator", "relpath_gen")

# Strategies
FILENAME = st.from_regex(
    r"[\w ]+" if platform.system() == "Windows" else r"[^/\0]+",
    fullmatch=True).map(str.strip).filter(lambda x: x.lstrip("."))

CONTENT = st.binary(min_size=3, max_size=300)


@st.composite
def relpath_gen(draw,
                filename: st.SearchStrategy[str] = FILENAME,
                dirname: typing.Optional[str] = None,
                max_depth: int = 5) -> st.SearchStrategy[str]:
    """
    A strategy to generate a relative path of a file.

    Parameters
    ----------
    filename : SearchStrategy[str], optional
        A strategy to create filenames.
    dirname : SearchStrategy[str], optional
        If specified, a different strategy is used for directory names,
        otherwise, the filename strategy is used instead.
    max_depth : int, optional
        The maximum directory depth that can be generated. The default is 5.
    """
    if dirname is None:
        dirname = filename
    parts = draw(st.lists(dirname, max_size=max_depth)) + [draw(filename)]
    return osp.join(*parts)


class FilesTreeGenerator(object):
    """
    A files and directory generator with Hypothesis strategies.

    It is a context manager.

    Parameters
    ----------
    root : os.PathLike
        A path to an existing empty directory.
    max_depth : int, optional
        The maximum directory depth that can be generated. The default is 5.
    """
    __slots__ = ("root", "max_depth", "_pool", "_futures")

    @staticmethod
    def update_files_with_changes(file_list: FILES,
                                  changes: FILE_CHANGES) -> FILES:
        """
        Apply changes to file list.

        Parameters
        ----------
        file_list : FILES
            The original file list.
        changes : FILE_CHANGES
            The changes to apply

        Returns
        -------
        FILES
            The given file list with changes applied.
        """
        for relpath, (change, content) in changes.items():
            if change in (ChangedStatus.ADDED, ChangedStatus.MODIFIED):
                file_list[relpath] = content
            elif change == ChangedStatus.DELETED and relpath in file_list:
                del file_list[relpath]

        return file_list

    def __init__(self, root: os.PathLike, max_depth: int = 5):
        super().__init__()
        self.root = Path(root)
        self.max_depth = max_depth
        self._pool = ThreadPoolExecutor(thread_name_prefix=root)
        self._futures = []

    def __enter__(self):
        """Start context manager."""
        return self

    def __exit__(self, *_):
        """Close internal threadpool."""
        self.close()

    def close(self) -> None:
        """Close generator and the internal threadpool."""
        self._pool.shutdown(wait=False)

    def apply_changes(self, changes: FILE_CHANGES) -> FILE_CHANGES:
        """
        A low-level method for applying changes.

        Any I/O task done here (except for directory making),
        is asynchrounous and some could be still in execution
        when the call ends.

        Parameters
        ----------
        changes : FILE_CHANGES
            A list of changes.

            Each item contains a :class:`~ChangedStatus` value
            and an object to generate that change.

        Returns
        -------
        FILE_CHANGES
            The same changes except that which cannot be applied.

        See Also
        --------
        is_running
            For checking if there are still I/O tasks running.
        wait
            For waiting unfinished tasks.
        """
        for relpath, (change, content) in changes.copy().items():
            relpath = Path(relpath)
            abspath = self.root / relpath

            if len(relpath.parts) - 1 > self.max_depth:
                # skip any path that exceed the max depth
                continue

            if change == ChangedStatus.ADDED:
                if not abspath.exists():
                    try:
                        os.makedirs(abspath.parent, exist_ok=True)
                    except (FileExistsError, NotADirectoryError):
                        del changes[str(relpath)]
                    else:
                        # Create dirs and the file
                        self._futures.append(
                            self._pool.submit(self._write_content, relpath,
                                              content))
                else:
                    del changes[str(relpath)]

            elif change == ChangedStatus.MODIFIED:
                if abspath.exists():
                    # Edit file
                    self._futures.append(
                        self._pool.submit(
                            self._write_content,
                            relpath,
                            content,
                            check_old=True,
                        ))
                else:
                    del changes[str(relpath)]

            elif change == ChangedStatus.DELETED:
                # Delete file/directory
                self._futures.append(self._pool.submit(self._delete, relpath))

        return changes

    # tasks operations
    @property
    def is_running(self) -> bool:
        """Check if there is any operations still running."""
        return bool(self._futures)

    def wait(self,
             suppress_errors: bool = False,
             task_timeout: typing.Optional[int] = None) -> None:
        """
        Wait until all tasks are done.

        Parameters
        ----------
        suppress_errors : bool, optional
            If True, any error raised by tasks is suppressed,
            otherwise it is raised. The default is False.
        task_timeout : typing.Optional[int], optional
            The timeout to wait for each task.
            If given, when timeout is reached, the task is considered done.
            The default is None.
        """
        def _task(future):
            with suppress(exc):
                future.result(timeout=task_timeout)

        if suppress_errors:
            exc = Exception
        else:
            exc = _TimeoutError

        with ThreadPoolExecutor() as pool:
            pool.map(_task, self._futures)

        self._futures = []

    # Hypothesis stuff
    @st.composite
    def create_tree(
        draw,
        self,
        filename: st.SearchStrategy[str] = FILENAME,
        dirname: typing.Optional[str] = None,
    ) -> FILES:
        """
        A strategy for generating a file tree.

        Parameters
        ----------
        filename : SearchStrategy[str], optional
            A strategy to create filenames.
        dirname : SearchStrategy[str], optional
            If specified, a different strategy is used for directory names,
            otherwise, the filename strategy is used instead.

        Returns
        -------
        dict
            A dict mapping each file path and its content.
        """
        files = draw(
            st.dictionaries(
                relpath_gen(
                    filename=filename,
                    dirname=dirname,
                    max_depth=self.max_depth,
                ),
                st.tuples(st.just(ChangedStatus.ADDED), CONTENT),
                min_size=1,
            ))

        files = self.apply_changes(files)
        self.wait()
        return dict(map(lambda item: (item[0], item[1][1]), files.items()))

    @st.composite
    def change_tree(
        draw,
        self,
        old_list: FILES,
        statuses=(
            ChangedStatus.ADDED,
            ChangedStatus.MODIFIED,
            ChangedStatus.DELETED,
        ),
        filename: st.SearchStrategy[str] = FILENAME,
        dirname: typing.Optional[str] = None,
        only_changes: bool = False,
    ) -> FILES:
        """
        A strategy for generating changes from an existing tree.

        Parameters
        ----------
        statuses : int
            A :class:`~ChangedStatus` value.
        filename : SearchStrategy[str], optional
            A strategy to create filenames.
        dirname : SearchStrategy[str], optional
            If specified, a different strategy is used for directory names,
            otherwise, the filename strategy is used instead.

        only_changes : bool
            If True, the done changes are returned,
            otherwise an updated list is returned instead.

        Returns
        -------
        FILES
            A dict that maps each file path and its content.
        FILE_CHANGES
            A dict containing changes.
        """
        changes = {}
        keys = sorted(old_list)

        if ChangedStatus.ADDED in statuses:
            changes.update(
                draw(
                    st.dictionaries(
                        relpath_gen(
                            filename=filename,
                            dirname=dirname,
                            max_depth=self.max_depth,
                        ).filter(lambda x: x not in keys),
                        st.tuples(st.just(ChangedStatus.ADDED), CONTENT),
                    )))
        if keys:
            if ChangedStatus.MODIFIED in statuses:
                changes.update(
                    draw(
                        st.dictionaries(
                            st.sampled_from(keys).filter(
                                lambda x: x not in changes),
                            st.tuples(st.just(ChangedStatus.MODIFIED),
                                      CONTENT),
                        )))

            if ChangedStatus.DELETED in statuses:
                changes.update(
                    draw(
                        st.dictionaries(
                            st.sampled_from(keys).filter(
                                lambda x: x not in changes),
                            st.tuples(st.just(ChangedStatus.DELETED),
                                      st.none()),
                        )))

        # Remove unchanged contents
        for relpath, (change, _) in changes.copy().items():
            if (change == ChangedStatus.MODIFIED
                    and old_list[relpath] == changes[relpath][1]):
                del changes[relpath]

        changes = self.apply_changes(changes)

        if not only_changes:
            new_list = self.update_files_with_changes(old_list, changes)

        self.wait()

        if only_changes:
            return changes

        return new_list

    # Private methods
    def _write_content(self,
                       relpath: os.PathLike,
                       content: typing.Union[bytes, str],
                       check_old: bool = False) -> None:

        is_binary = isinstance(content, (bytes, bytearray))
        abspath = self.root / relpath
        if check_old:
            with open(abspath, "rb" if is_binary else "r") as stream:
                if stream.read() == content:
                    raise ValueError(
                        "Given content is the same of file content.")

        with open(self.root / relpath, "wb" if is_binary else "w") as stream:
            stream.write(content)

    def _delete(self, relpath: os.PathLike) -> None:
        abspath = (self.root / relpath)
        if abspath.is_dir():
            shutil.rmtree(abspath)
        else:
            abspath.unlink()
