#!/bin/bash

# puts changes from upstream to downstream repository.

# This script contains no "exit" since it is intended to be sourced like in
# "bash <scriptname>". This is needed since when darcs is the upstream
# repository, it cannot manage the file executable mode, so in this case
# no files in the checked out repository are executable.

SCRIPT_FULL_NAME=$(readlink -e "$0")
MYDIR=$(dirname "$SCRIPT_FULL_NAME")
MYNAME=$(basename "$SCRIPT_FULL_NAME")

# define project directory, this is used in config.dat (see below):
PROJECT_DIR=$(readlink -e "$MYDIR/..")

function print_short_help {
    echo "$MYNAME - convert upstream to downstream repository."
    echo 
    echo "usage:"
    echo "$MYNAME OPTIONS"
    echo "Known options:"
    echo "-h : this help"
    echo "--first: Skip downloading the downstream repository from"
    echo "    the repository hoster. Do this when the downstream repository"
    echo "    at the repository hoster is not yet created."
    exit 0
}

FIRST=""

declare -a ARGS
skip_options=""

while true; do
    case "$1" in
        -h | --help)
            print_short_help
            ;;
        --first)
            FIRST="YES";
            shift
            ;;
        -- )
            skip_options="yes"
            shift;
            break
            ;;
        *)
            if [ -z "$1" ]; then
                break;
            fi
            if [[ $1 =~ ^- ]]; then
                echo "unknown option: $1"
                exit 1
            fi
            ARGS+=("$1")
            shift
            ;;
    esac
done

if [ -n "$skip_options" ]; then
    while true; do
        if [ -z "$1" ]; then
            break;
        fi
        ARGS+=("$1")
        shift
    done
fi

for arg in "${ARGS[@]}"; do
    # examine extra args
    # match known args here like:
    # if [ "§arg" == "doit" ]; then ...
    #     continue
    # fi
    echo "unexpeced argument: $arg"
    exit 1
done

# define configuration variables, all thes names start with "CNF_":
. "$MYDIR/config.dat"
. "$MYDIR/functions.sh"

if [ "${#CNF_UPSTREAM_REPOS[@]}" -ne 0 ]; then
    echo "Error, CNF_UPSTREAM_REPOS is not empty, upstream repository"
    echo "branches are defined."
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

if [ -n "$(cnf_repo_check $CNF_DOWNSTREAM_REPO_TYPE)" ]; then
    echo "ERROR, there is already a $CNF_DOWNSTREAM_REPO_TYPE repository here!" >&2
    exit 1
fi

MAIN_CONV_REPO="$CNF_NAME-downstream"

cd "$PROJECT_DIR/.." || exit 1

# create or clone the main downstream repo:
# note: this is NOT a bare repo
if [ -z "$FIRST" ]; then
    # Download repo from downstream hoster:
    cnf_ask_delete_dir "$MAIN_CONV_REPO"
    cnf_repo_clone "$CNF_DOWNSTREAM_REPO_TYPE" "$CNF_DOWNSTREAM_REPO" "$MAIN_CONV_REPO"
fi

if [ "$CNF_UPSTREAM_REPO_TYPE" == "$CNF_DOWNSTREAM_REPO_TYPE" ]; then
    # same repository type, just pull patches:
    (cd "$MAIN_CONV_REPO" && cnf_repo_pull "$CNF_UPSTREAM_REPO_TYPE" "../$PROJECT_DIR")
else
    # convert the repository:
    cnf_repo_convert "$PROJECT_DIR" "$MAIN_CONV_REPO" "$CNF_DOWNSTREAM_REPO_TYPE" $CNF_MIRROR_OPT
fi

PARENT_DIR=$(dirname "$PROJECT_DIR")

echo
echo "==========================================================="
echo "Finished, the $CNF_DOWNSTREAM_REPO_TYPE repository is in directory:"
echo "    $PARENT_DIR/$MAIN_CONV_REPO"
echo
echo "You may push these changes to the downstream repository"
echo "with:"
echo "    cd $PARENT_DIR/$MAIN_CONV_REPO"
echo "    bash administration_tools/downstream-push.sh"
echo
echo "Note that you MUST NOT create any other new commits"
echo "in the downstream repository."
echo "==========================================================="


