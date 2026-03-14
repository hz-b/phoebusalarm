#!/bin/sh

SCRIPT_FULL_NAME=$(readlink -e $0)
MYDIR=$(dirname -- "$SCRIPT_FULL_NAME")
MYNAME=$(basename -- "$SCRIPT_FULL_NAME")

if [ "$1" = "-h" -o "$1" = "--help" ]; then
    echo "$MYNAME"
    echo "Installs this project locally in directories 'bin' and 'lib'."
    echo
    echo "Usage:"
    echo "  $MYNAME"
    exit 0
fi

cd "$MYDIR"

VER=$(pip3 --version | sed -e 's/^pip \+//;s/ .*//')
if [ -z "$VER" ]; then
    echo "error, pip3 not found, exiting..." >&2
    exit 1
fi

MAJOR_VER=$(echo $VER | sed -e 's/\..*//')

if [ "$MAJOR_VER" -le 19 ]; then
    # very old pip, can't properly use the pyproject.toml
    echo "error, version ${VER} of pip is too old, needs >19, exiting..." >&2
    exit 1
else
    # modern pip, we create a venv to sidestep all the annyoing Debian changes to pip.
    # This should give a more consistent result, ignoring most PYTHONUSERBASE and PYTHONPATH settings.
    python3 -m venv venv && . venv/bin/activate && pip install --no-deps --no-warn-script-location --prefix . .
fi

