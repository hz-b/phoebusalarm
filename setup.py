from setuptools import setup, find_packages
import os

this_directory = os.path.split(os.path.abspath(__file__))[0]

with open(os.path.join(this_directory, "README.md"), "r") as readme:
    long_description = readme.read()

setup(
    name='phoebusalarm',
    python_requires='>=3.5',
    version='1.0.1',
    description='Python Utilities for Pheobus',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Malte Gotz',
    author_email='malte.gotz@helmholtz-berlin.de',
    url='https://gitlab.helmholtz-berlin.de/acs/pyphoebus/',
    license="GPL v3",
    packages=find_packages(include=['phoebusalarm']),
    install_requires=['treelib'],
)
