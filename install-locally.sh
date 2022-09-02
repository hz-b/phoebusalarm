#!/bin/bash

SCRIPT_FULL_NAME=$(readlink -e $0)
MYDIR=$(dirname $SCRIPT_FULL_NAME)
MYNAME=$(basename $SCRIPT_FULL_NAME)

if [ "$1" == "-h" -o "$1" == "--help" ]; then
    echo "$MYNAME"
    echo "Installs this project locally in directories 'bin' and 'lib'."
    echo
    echo "Usage:"
    echo "  $MYNAME"
    exit 0
fi

cd "$MYDIR"

if [ ! -e "setup.py" ]; then
    echo "error, setup.py not found, exiting..." >&2
    exit 1
fi

VER=$(pip3 --version | sed -e 's/^pip \+//;s/ .*//')
if [ -z "$VER" ]; then
    echo "error, pip3 not found, exiting..." >&2
    exit 1
fi

MAJOR_VER=$(echo $VER | sed -e 's/\..*//')

if (( $MAJOR_VER <= 9 )); then
    # very old python3 version, cannot use pip
    python3 setup.py install --prefix=. --single-version-externally-managed --root .
else
    # modern pip, we can use pip:
    pip install --prefix . --no-warn-script-location --no-cache-dir .
fi

