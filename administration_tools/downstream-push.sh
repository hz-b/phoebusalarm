#!/bin/bash

# This script contains no "exit" since it is intended to be sourced like in
# "bash <scriptname>". This is needed since when darcs is the upstream
# repository, it cannot manage the file executable mode, so in this case
# no files in the checked out repository are executable.

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

    if [ -z "$(cnf_repo_check $CNF_DOWNSTREAM_REPO_TYPE)" ]; then
        echo "ERROR, there is no $CNF_DOWNSTREAM_REPO_TYPE repository here!" >&2
        break
    fi
    cnf_repo_push "$CNF_DOWNSTREAM_REPO_TYPE" "$CNF_DOWNSTREAM_REPO"
    break
done

