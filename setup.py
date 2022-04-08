# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# -----------------------------------------------------------------------------
"""Setup script for spyder_vcs."""

# Standard library imports
import ast
import os

# Third party imports
from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def get_version(module='spyder_vcs'):
    """Get version."""
    with open(os.path.join(HERE, module, '__init__.py'), 'r') as f:
        data = f.read()
    lines = data.split('\n')
    for line in lines:
        if line.startswith('VERSION_INFO'):
            version_tuple = ast.literal_eval(line.split('=')[-1].strip())
            version = '.'.join(map(str, version_tuple))
            break
    return version


def get_description():
    """Get long description."""
    with open(os.path.join(HERE, 'README.md'), 'r') as f:
        data = f.read()
    return data


REQUIREMENTS = [
    # 'spyder>5.3.0',
]

EXTRAS_REQUIRE = {
}


setup(
    name='spyder-vcs',
    version=get_version(),
    keywords=['Spyder', 'Plugin'],
    url='https://github.com/spyder-ide/spyder-vcs',
    license='MIT',
    author='Spyder Project Contributors',
    author_email='spyder.python@gmail.com',
    description='Spyder Plugin for VCSs',
    long_description=get_description(),
    long_description_content_type='text/x-md',
    packages=find_packages(exclude=['contrib', 'docs']),
    install_requires=REQUIREMENTS,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
        ],
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        "spyder.plugins": [
            "vcs = spyder_vcs.plugin:VCS"
        ],
    })
