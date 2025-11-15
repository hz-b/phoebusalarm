#!/bin/bash

# This script contains no "exit" since it is intended to be sourced like in
# "bash <scriptname>". This is needed since darcs cannot manage the file
# executable mode, so as a default in darcs no files are executable.

SCRIPT_FULL_NAME=$(readlink -e "$0")
MYDIR=$(dirname "$SCRIPT_FULL_NAME")
#MYNAME=$(basename "$SCRIPT_FULL_NAME")

# define project directory, this is used in config.dat (see below):
PROJECT_DIR=$(readlink -e "$MYDIR/..")

# define configuration variables, all thes names start with "CNF_":
. "$MYDIR/config.dat"
. "$MYDIR/functions.sh"

while true; do

    cd "$PROJECT_DIR" || break

    cnf_repo_push "$CNF_UPSTREAM_REPO_TYPE" "$CNF_UPSTREAM_REPO" "$@"
    break
done

