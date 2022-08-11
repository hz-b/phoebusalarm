# Phoebus Alarm

A Python package to create alarm configurations for Phoebus
https://controlssoftware.sns.ornl.gov/css_phoebus/

## Requirements
Python >= 3.5

## Installation
Use pip to install the package
```
pip install .
```
alternatively you can run the convert_aly.py script directly.

## Usage
This package has two intended usages: Converting Alarm Handler configurations to Phoebus and facilitating the creation of Phoebus alarm configs with Python scripts.
Run `python convert_alh.py -h` to see about the scripts usage for converting alh to phoebus configs.
See the alarmtree module's help/documentation on how to use it to build an alarm tree in Phyton and exporting it to Phoebus xml.
