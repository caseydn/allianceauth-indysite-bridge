"""Compatibility shim. All real metadata lives in pyproject.toml; this exists so
older pip/setuptools that look for setup.py can still build the package.
"""

from setuptools import setup

setup()
