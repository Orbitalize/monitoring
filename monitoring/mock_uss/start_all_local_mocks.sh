#!/bin/bash

set -eo pipefail

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

if [ -n "${NRIA_LICENSE_KEY}" ]; then
#  curl -Ls https://download.newrelic.com/install/newrelic-cli/scripts/install.sh | bash && sudo NEW_RELIC_API_KEY="${NEW_RELIC_API_KEY}" NEW_RELIC_ACCOUNT_ID="${NEW_RELIC_ACCOUNT_ID}" NEW_RELIC_REGION=EU /usr/local/bin/newrelic install -y
  docker run \
  -d \
  --name newrelic-infra \
  --network=host \
  --cap-add=SYS_PTRACE \
  --privileged \
  --pid=host \
  -v "/:/host:ro" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  -e NRIA_LICENSE_KEY="${NRIA_LICENSE_KEY}" \
  newrelic/infrastructure:latest
fi

monitoring/mock_uss/run_locally_scdsc.sh -d
export DO_NOT_BUILD_MONITORING=true
monitoring/mock_uss/run_locally_ridsp.sh -d
monitoring/mock_uss/run_locally_riddp.sh -d
monitoring/mock_uss/run_locally_geoawareness.sh -d
monitoring/mock_uss/run_locally_atproxy_client.sh -d
monitoring/mock_uss/run_locally_tracer.sh -d
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_scdsc
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_ridsp
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_riddp
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_geoawareness
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_tracer
