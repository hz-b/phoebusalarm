from setuptools import setup, find_packages
import versioneer

setup(
    name='phoebusalarm',
    python_requires='>=3.5',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(include=['phoebusalarm']),
    install_requires=['treelib']
)
