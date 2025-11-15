# -------------------------------------
# functions, do not change this
# -------------------------------------

function cnf_ask_delete_dir {
    # ask if an existing directory shoudl be deleted
    local DIR="$1"
    if [ ! -d "$DIR" ]; then
        return
    fi
    echo "$DIR already exists."
    echo "Delete it ? Answer 'Y' to delete, everythng else aborts"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "aborted"
        break
    fi
    rm -rf "$DIR"
}

function cnf_repo_clone {
    # does a "clone" command for the repository type
    # $1: repo type
    # $2: source
    # $3: dest
    if [ "$1" == "git" ]; then
        git clone "$2" "$3"
    elif [ "$1" == "mercurial" ]; then
        hg clone "$2" "$3"
    elif [ "$1" == "darcs" ]; then
        darcs get "$2" "$3"
    else
        echo "ERROR, unknown repo type: $1" >&2
        exit 1
    fi
    if [ $? -ne 0 ]; then
        echo "ERROR, cnf_repo_clone failed"
        exit 1
    fi
}

function cnf_repo_push {
    # does a "push" command for the repository type
    # $1: repo type
    # $2: dest
    # $3 .. $n: extra arguments
    local tp="$1"
    shift
    local dest="$1"
    shift
    if [ "$tp" == "git" ]; then
        git push --mirror "$dest" "$@"
    elif [ "$tp" == "mercurial" ]; then
        hg push "$dest" "$@"
    elif [ "$tp" == "darcs" ]; then
        darcs push "$dest" "$@"
    else
        echo "ERROR, unknown repo type: $tp" >&2
    fi
    if [ $? -ne 0 ]; then
        echo "ERROR, cnf_repo_push failed"
        exit 1
    fi
}

function cnf_repo_pull {
    # does a "pull" command for the repository type
    # $1: repo type
    # $2: remote
    # $3 .. $n: extra arguments
    local tp="$1"
    shift
    local dest="$1"
    shift
    if [ "$tp" == "git" ]; then
        git pull "$dest" "$@"
    elif [ "$tp" == "mercurial" ]; then
        hg pull "$dest" "$@"
    elif [ "$tp" == "darcs" ]; then
        darcs pull "$dest" "$@"
    else
        echo "ERROR, unknown repo type: $tp" >&2
    fi
    if [ $? -ne 0 ]; then
        echo "ERROR, cnf_repo_pull failed"
        exit 1
    fi
}

function cnf_repo_revert {
    # does a "revert" command for the repository type
    # $1: repo type
    if [ "$1" == "git" ]; then
        git reset --hard
    elif [ "$1" == "mercurial" ]; then
        hg revert -a
    elif [ "$1" == "darcs" ]; then
        darcs revert -a
    else
        echo "ERROR, unknown repo type: $1" >&2
    fi
    if [ $? -ne 0 ]; then
        echo "ERROR, cnf_repo_revert failed"
        exit 1
    fi
}

function cnf_repo_check {
    # checks if the repository directory is present
    # returns "yes" or ""
    # $1: repo type
    if [ "$1" == "git" ]; then
        if [ -d .git ]; then
            echo "yes"
        fi
    elif [ "$1" == "mercurial" ]; then
        if [ -d .hg ]; then
            echo "yes"
        fi
    elif [ "$1" == "darcs" ]; then
        if [ -d _darcs ]; then
            echo "yes"
        fi
    fi
}

REPO_MIRROR_CHECKED=""

function cnf_repo_convert {
    # convert repo with repo-mirror.sh utility
    # $1: SRC
    # $2: DEST
    # $3: REPOTYPE
    # $4 .. $n: extra arguments
    local SRC="$1"
    shift
    local DEST="$1"
    shift
    local TYPE="$1"
    shift
    if [ -z "$REPO_MIRROR_CHECKED" ]; then
        if ! repo-mirror.sh -h >/dev/null 2>&1; then
            echo "ERROR, repo-mirror.sh not found. This is part of bii_scripts." >&2
            echo "You can download bii_scripts at:" >&2
            echo "    https://bii-scripts.sourceforge.io/" >&2
            exit 1
        fi
    fi
    repo-mirror.sh "$SRC" "$DEST" -t "$TYPE" "$@"
    if [ $? -ne 0 ]; then
        echo "ERROR, cnf_repo_convert failed"
        exit 1
    fi
}

function cnf_repo_hash {
    # returns logical true when the repository was changed
    # $1: repository
    repo-hash.sh "$1" "$1/repo.hash"
}

function git_branch_merge {
    # $1: dest_repo
    # $2: other_repo
    # $3: branch_name
    # $4... extra options
    local MYREPO="$1"
    shift
    local OTHERREPO="$1"
    shift
    local BRANCHNAME="$1"
    shift
    
    git-repo-merge.sh "$MYREPO" "$OTHERREPO" "$BRANCHNAME" "$@"
    if [ $? -ne 0 ]; then
        echo "ERROR, git_branch_merge failed"
        exit 1
    fi
}
