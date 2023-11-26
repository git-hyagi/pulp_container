#!/bin/bash

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_container' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

set -mveuo pipefail

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

source .github/workflows/scripts/utils.sh

export PULP_URL="${PULP_URL:-https://pulp}"

pip install twine wheel

REPORTED_STATUS="$(pulp status)"
REPORTED_VERSION="$(echo "$REPORTED_STATUS" | jq --arg plugin "container" -r '.versions[] | select(.component == $plugin) | .version')"
VERSION="$(echo "$REPORTED_VERSION" | python -c 'from packaging.version import Version; print(Version(input()))')"

pushd ../pulp-openapi-generator
rm -rf pulp_container-client
./generate.sh pulp_container python "$VERSION"
pushd pulp_container-client
python setup.py sdist bdist_wheel --python-tag py3

twine check "dist/pulp_container_client-$VERSION-py3-none-any.whl" || exit 1
twine check "dist/pulp_container-client-$VERSION.tar.gz" || exit 1

cmd_prefix pip3 install "/root/pulp-openapi-generator/pulp_container-client/dist/pulp_container_client-${VERSION}-py3-none-any.whl"
tar cvf ../../pulp_container/container-python-client.tar ./dist

find ./docs/* -exec sed -i 's/Back to README/Back to HOME/g' {} \;
find ./docs/* -exec sed -i 's/README//g' {} \;
cp README.md docs/index.md
sed -i 's/docs\///g' docs/index.md
find ./docs/* -exec sed -i 's/\.md//g' {} \;
tar cvf ../../pulp_container/container-python-client-docs.tar ./docs
popd
popd
