#!/bin/sh -e

# install weboob inside a virtualenv, optionally with an associated weboob workdir
# can be combined with git-worktree

cd "$(dirname $0)/.."
SRC=$PWD

source=
VDIR=

usage () {
    cat << EOF
Usage: $0 [-s] [-d DIR]
  -s            point sources.list to $SRC/modules instead of updates.weboob.org
  -d DIR        install virtualenv in DIR instead of a new dir
EOF
}

while getopts hsd: name
do
    case $name in
    s) source=y;;
    d) VDIR="$OPTARG";;
    h) usage
       exit 0;;
    ?) usage
       exit 2;;
    esac
done
shift $(($OPTIND - 1))

PYTHON=${PYTHON-python3}

echo "Using weboob source $SRC"

if [ -z "$VDIR" ]
then
    VDIR=$(mktemp -d /tmp/weboob.venv.XXXXXX)
fi

cd "$VDIR"
echo "Creating env in $VDIR"

virtualenv -p "$(which "$PYTHON")" --system-site-packages "$VDIR"
. ./bin/activate

echo "Installing weboob in $VDIR"
"$PYTHON" -m pip install "$SRC"

mkdir workdir
export WEBOOB_WORKDIR=$VDIR/workdir

if [ "$source" = y ]
then
    echo "file://$SRC/modules" > "$WEBOOB_WORKDIR/sources.list"
fi

cat > use-weboob-local.sh << EOF
VDIR="$VDIR"
. "$VDIR/bin/activate"
export WEBOOB_WORKDIR="$VDIR/workdir"
EOF

cat << EOF
Installation complete in $VDIR.
Run ". $VDIR/use-weboob-local.sh" to start using it.
Run "$PYTHON -m pip install -U $SRC" to reinstall the core.
EOF

if [ "$source" != y ]
then
    echo "You can add file://$SRC/modules into $VDIR/workdir/sources.list to use local modules instead of downloading modules."
fi

./bin/weboob-config update
