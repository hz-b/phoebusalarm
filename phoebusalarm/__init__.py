# -*- coding: utf-8 -*-
"""
init file
"""

try:
    # when created by setuptools_scm at build time this file exists
    from ._version import __version__  # type: ignore
except Exception:
    try:
        # runtime fallback for local dev/tests (requires setuptools_scm installed)
        from setuptools_scm import get_version as _get_version

        __version__ = _get_version(root="..", relative_to=__file__)
    except Exception:
        # final fallback if no git metadata / setuptools_scm not installed
        __version__ = "0+unknown"
