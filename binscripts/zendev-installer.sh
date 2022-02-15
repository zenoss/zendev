#!/usr/bin/env bash

set -eu

panic() {
	tput sgr0
	tput setaf 1
	echo
	echo "ERROR: $1" >&2
	echo
	tput sgr0
	exit 1
}

trap 'panic "Script failed at line ${LINENO}"' ERR

# Test $# for argument count == 1 first otherwise $1 is an unset variable
# and triggers an error.
if [ $# -eq 1 ] && [ -n "$1" ]; then
	SRC_ROOT="${HOME}/$1"
else
	SRC_ROOT="${HOME}/src"
fi

BRANCH=zendev2
ZENDEV_DIR=${SRC_ROOT}/zendev
ZENDEV_REPO=git@github.com:zenoss/zendev.git

if [ "$(uname)" == "Darwin" ]; then
	ENV_FILE=${HOME}/.profile
else
	ENV_FILE=${HOME}/.bashrc
fi

# if no zendev or zendev version command fails (only v2 has version option)
if ! zendev version >/dev/null 2>&1 ; then

	if ! git --help >/dev/null 2>&1 ; then
		panic "Please install git before running this script"
	fi

	echo
	echo "Installing zendev to ${ZENDEV_DIR}"

	[ -d "${SRC_ROOT}" ] || mkdir -p ${SRC_ROOT} >/dev/null 2>&1

	if [ -d "${ZENDEV_DIR}" ]; then
		echo "${ZENDEV_DIR} exists.  Assuming the zendev repo is already cloned."
	else
		git clone ${ZENDEV_REPO} ${ZENDEV_DIR}
	fi

	pushd . >/dev/null
	cd ${ZENDEV_DIR}
	git checkout ${BRANCH} >/dev/null 2>&1
	pip install --user --no-color --progress-bar off --disable-pip-version-check --no-python-version-warning -e .
	popd >/dev/null

	cat <<EOF>> ${ENV_FILE}

# Initialize zendev environment
source $(zendev bootstrap)
EOF
else
	echo
	echo "zendev already installed"
fi

if ! gvm >/dev/null 2>&1; then
	echo
	echo "Installing gvm"
	curl -sSL https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer | bash

	source ${HOME}/.gvm/scripts/gvm
	gvm install go1.10.8 --binary
	gvm install go1.17.7 --binary
else
	echo
	echo "gvm already installed"
fi

source ${HOME}/.gvm/scripts/gvm
set +u
gvm use go1.17.7 --default >/dev/null
set -u

if ! hub help >/dev/null 2>&1; then
	echo
	echo "Installing hub"
	GOPATH=${HOME}/.local go install github.com/github/hub@latest

	cat <<EOF>> ${ENV_FILE}

# Setup hub completion
if [ -f ${HOME}/.local/pkg/mod//github.com/github/hub*/etc/hub.bash_completion.sh ]; then
	source \${HOME}/.local/pkg/mod//github.com/github/hub*/etc/hub.bash_completion.sh
fi
EOF
else
	echo
	echo "hub already installed"
fi

if ! jig >/dev/null 2>&1; then
	echo
	echo "Installing jig"
	set +u
	gvm use go1.10.8 >/dev/null
	set -u
	GOPATH=${HOME}/.local go get github.com/iancmcc/jig
	set +u
	gvm use go1.17.7 >/dev/null
	set -u
else
	echo
	echo "jig already installed"
fi

MAX_MAP_COUNT=262144

if [[ $(sysctl -b vm.max_map_count) -lt ${MAX_MAP_COUNT} ]]; then
	echo
	echo "Setting vm.max_map_count system parameter to ${MAX_MAP_COUNT}"
	echo "vm.max_map_count=${MAX_MAP_COUNT}" | sudo tee /etc/sysctl.d/60-serviced.conf >/dev/null
	sudo sysctl --system >/dev/null
else
	echo
	echo "The vm.max_map_count system parameter already set."
fi

MAX_OPEN_FILES=1048576
LIMITS_CHANGED="N"

if [[ $(ulimit -Sn) -lt ${MAX_OPEN_FILES} ]]; then
	echo
	echo "Setting the upper limit for open files to ${MAX_OPEN_FILES}"
	cat <<EOF | sudo tee /etc/security/limits.d/serviced.conf >/dev/null
# Control Center requires the hard/soft limits for open files to be at least ${MAX_OPEN_FILES}.
*     hard  nofile  ${MAX_OPEN_FILES}
*     soft  nofile  ${MAX_OPEN_FILES}
root  hard  nofile  ${MAX_OPEN_FILES}
root  soft  nofile  ${MAX_OPEN_FILES}
EOF
	LIMITS_CHANGED="Y"
else
	echo
	echo "The upper limit for open files is already set to ${MAX_OPEN_FILES}."
fi

echo
if [ ${LIMITS_CHANGED} = "N" ]; then
	echo "Please relogin or run 'source ~/.bashrc' to make changes take effect."
else
	echo "Please relogin to make changes take effect."
fi
