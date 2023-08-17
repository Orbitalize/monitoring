#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ -z "${DO_NOT_BUILD_MONITORING}" ]; then
  "${SCRIPT_DIR}/../build.sh" || exit 1
fi

AUTH="DummyOAuth(http://host.docker.internal:8085/token,uss1)"
DSS="http://host.docker.internal:8082"
PUBLIC_KEY="/var/test-certs/auth2.pem"
AUD=${MOCK_USS_TOKEN_AUDIENCE:-localhost,host.docker.internal}
CONTAINER_NAME=${CONTAINER_NAME:-"mock_uss_scdsc"}

PORT=${PORT:-8074}
BASE_URL="http://${MOCK_USS_TOKEN_AUDIENCE:-host.docker.internal}:${PORT}"

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args="-it"
fi

docker container rm -f "${CONTAINER_NAME}" || echo "No pre-existing ${CONTAINER_NAME} container to remove"

# shellcheck disable=SC2086
docker run ${docker_args} --name "${CONTAINER_NAME}" \
  --ulimit nofile=10000 \
  -e MOCK_USS_AUTH_SPEC="${AUTH}" \
  -e MOCK_USS_DSS_URL="${DSS}" \
  -e MOCK_USS_PUBLIC_KEY="${PUBLIC_KEY}" \
  -e MOCK_USS_TOKEN_AUDIENCE="${AUD}" \
  -e MOCK_USS_BASE_URL="${BASE_URL}" \
  -e MOCK_USS_SERVICES="scdsc" \
  -p ${PORT}:5000 \
  -v "${SCRIPT_DIR}/../../build/test-certs:/var/test-certs:ro" \
  "$@" \
  interuss/monitoring \
  mock_uss/start.sh
