#!/bin/bash
if [ -z "$PYTHON" ]
then
echo 'Set $PYTHON then run again. Exting.'
exit 1
fi

$PYTHON setup.py sdist bdist_wheel
$PYTHON setup.py generate_stubs

export NAWAH_API_LEVEL=$($PYTHON setup.py api_level | tail -n 1)
export NAWAH_VERSION=$($PYTHON setup.py version | tail -n 1)

rm -rf nawah_framework_wheels
git clone https://github.com/nawah-io/nawah_framework_wheels

rm -rf nawah_framework_wheels/$NAWAH_API_LEVEL
mkdir nawah_framework_wheels/$NAWAH_API_LEVEL
cp dist/nawah-$NAWAH_VERSION-py3-none-any.whl nawah_framework_wheels/$NAWAH_API_LEVEL/nawah.whl
cp requirements.txt nawah_framework_wheels/$NAWAH_API_LEVEL
cp out/nawah/stubs.tar.gz nawah_framework_wheels/$NAWAH_API_LEVEL
echo -n $NAWAH_VERSION > nawah_framework_wheels/$NAWAH_API_LEVEL/version.txt

if [[ "$*" == *--deploy* ]]
then
    git log -1 --pretty=%B > commit_msg
	cd nawah_framework_wheels
	git add .
	git commit -m "$(cat ../commit_msg)"
	git tag APIv$NAWAH_VERSION
	echo 'Inspect and push changes and tags from nawah_framework_wheels'
fi