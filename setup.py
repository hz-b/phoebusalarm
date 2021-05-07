from setuptools import setup, find_packages

setup(
    name='phoebusalarm',
    python_requires='>3.8',
    version='0.1.0',
    packages=find_packages(include=['phoebusalarm']),
    install_requires=['treelib']
)
