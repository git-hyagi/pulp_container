#!/usr/bin/env bash

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_container' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..
REPO_ROOT="$PWD"

set -euv

source .github/workflows/scripts/utils.sh

PLUGIN_VERSION="$(sed -n -e 's/^\s*current_version\s*=\s*//p' .bumpversion.cfg | python -c 'from packaging.version import Version; print(Version(input()))')"
PLUGIN_SOURCE="./pulp_container/dist/pulp_container-${PLUGIN_VERSION}-py3-none-any.whl"

export PULP_API_ROOT="/pulp/"

PIP_REQUIREMENTS=("pulp-cli")

# This must be the **only** call to "pip install" on the test runner.
pip install ${PIP_REQUIREMENTS[*]}

# Check out the pulp-cli branch matching the installed version.
PULP_CLI_VERSION="$(pip freeze | sed -n -e 's/pulp-cli==//p')"
git clone --depth 1 --branch "$PULP_CLI_VERSION" https://github.com/pulp/pulp-cli.git ../pulp-cli

cd .ci/ansible/
if [ "$TEST" = "s3" ]; then
  PLUGIN_SOURCE="${PLUGIN_SOURCE} pulpcore[s3]"
fi
if [ "$TEST" = "azure" ]; then
  PLUGIN_SOURCE="${PLUGIN_SOURCE} pulpcore[azure]"
fi

cat >> vars/main.yaml << VARSYAML
image:
  name: pulp
  tag: "ci_build"
plugins:
  - name: pulp_container
    source: "${PLUGIN_SOURCE}"
VARSYAML
if [[ -f ../../ci_requirements.txt ]]; then
  cat >> vars/main.yaml << VARSYAML
    ci_requirements: true
VARSYAML
fi
if [ "$TEST" = "pulp" ]; then
  cat >> vars/main.yaml << VARSYAML
    upperbounds: true
VARSYAML
fi
if [ "$TEST" = "lowerbounds" ]; then
  cat >> vars/main.yaml << VARSYAML
    lowerbounds: true
VARSYAML
fi

cat >> vars/main.yaml << VARSYAML
services:
  - name: pulp
    image: "pulp:ci_build"
    volumes:
      - ./settings:/etc/pulp
      - ./ssh:/keys/
      - ~/.config:/var/lib/pulp/.config
      - ../../../pulp-openapi-generator:/root/pulp-openapi-generator
    env:
      PULP_WORKERS: "4"
      PULP_HTTPS: "true"
VARSYAML

cat >> vars/main.yaml << VARSYAML
pulp_env: {}
pulp_settings: {"allowed_content_checksums": ["sha1", "sha224", "sha256", "sha384", "sha512"], "allowed_export_paths": ["/tmp"], "allowed_import_paths": ["/tmp"]}
pulp_scheme: https
pulp_default_container: ghcr.io/pulp/pulp-ci-centos:latest
VARSYAML

if [ "$TEST" = "s3" ]; then
  export MINIO_ACCESS_KEY=AKIAIT2Z5TDYPX3ARJBA
  export MINIO_SECRET_KEY=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
  sed -i -e '/^services:/a \
  - name: minio\
    image: minio/minio\
    env:\
      MINIO_ACCESS_KEY: "'$MINIO_ACCESS_KEY'"\
      MINIO_SECRET_KEY: "'$MINIO_SECRET_KEY'"\
    command: "server /data"' vars/main.yaml
  sed -i -e '$a s3_test: true\
minio_access_key: "'$MINIO_ACCESS_KEY'"\
minio_secret_key: "'$MINIO_SECRET_KEY'"\
pulp_scenario_settings: null\
pulp_scenario_env: {}\
' vars/main.yaml
  export PULP_API_ROOT="/rerouted/djnd/"
fi

if [ "$TEST" = "azure" ]; then
  sed -i -e '/^services:/a \
  - name: ci-azurite\
    image: mcr.microsoft.com/azure-storage/azurite\
    volumes:\
      - ./azurite:/etc/pulp\
    command: "azurite-blob --blobHost 0.0.0.0"' vars/main.yaml
  sed -i -e '$a azure_test: true\
pulp_scenario_settings: null\
pulp_scenario_env: {}\
' vars/main.yaml
fi

echo "PULP_API_ROOT=${PULP_API_ROOT}" >> "$GITHUB_ENV"

if [ "${PULP_API_ROOT:-}" ]; then
  sed -i -e '$a api_root: "'"$PULP_API_ROOT"'"' vars/main.yaml
fi

pulp config create --base-url https://pulp --api-root "$PULP_API_ROOT" --username "admin" --password "password"
cp ~/.config/pulp/cli.toml "${REPO_ROOT}/../pulp-cli/tests/cli.toml"

ansible-playbook build_container.yaml
ansible-playbook start_container.yaml

# .config needs to be accessible by the pulp user in the container, but some
# files will likely be modified on the host by post/pre scripts.
chmod 777 ~/.config/pulp_smash/
chmod 666 ~/.config/pulp_smash/settings.json
# Plugins often write to ~/.config/pulp/cli.toml from the host
chmod 777 ~/.config/pulp
chmod 666 ~/.config/pulp/cli.toml
sudo chown -R 700:700 ~/.config
echo ::group::SSL
# Copy pulp CA
sudo docker cp pulp:/etc/pulp/certs/pulp_webserver.crt /usr/local/share/ca-certificates/pulp_webserver.crt

# Hack: adding pulp CA to certifi.where()
CERTIFI=$(python -c 'import certifi; print(certifi.where())')
cat /usr/local/share/ca-certificates/pulp_webserver.crt | sudo tee -a "$CERTIFI" > /dev/null

# Hack: adding pulp CA to default CA file
CERT=$(python -c 'import ssl; print(ssl.get_default_verify_paths().openssl_cafile)')
cat /usr/local/share/ca-certificates/pulp_webserver.crt | sudo tee -a "$CERT" > /dev/null

# Updating certs
sudo update-ca-certificates
echo ::endgroup::

if [[ "$TEST" = "azure" ]]; then
  AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://ci-azurite:10000/devstoreaccount1;'
  az storage container create --name pulp-test --connection-string $AZURE_STORAGE_CONNECTION_STRING
fi

echo ::group::PIP_LIST
cmd_prefix bash -c "pip3 list && pipdeptree"
echo ::endgroup::
