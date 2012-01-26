#!/bin/bash

RELEASE_NUM=`grep version setup.py | cut -d\' -f2`

# Push to PyPi
./setup.py sdist upload

# Tag in Git
git tag $RELEASE_NUM -m "Tagging release $RELEASE_NUM"
git push --tags