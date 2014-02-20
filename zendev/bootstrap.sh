ZENDEV_SCRIPT="$(which zendev)"

zendev () {
    PID=$$
    export ZDCTLCHANNEL=$(mktemp -u /tmp/zd.${PID}.XXXXXXX)
    ${ZENDEV_SCRIPT} $@
    source "${ZDCTLCHANNEL}" > /dev/null 2>&1
    rm -f ${ZDCTLCHANNEL}
    unset ZDCTLCHANNEL
}

alias cdz="zendev cd"

if [ ${BASH_VERSION:0:1} -ge 4 ]; then
    ZENDEV_ARGCOMPLETE=$(mktemp -u /tmp/zd.argcomplete.XXXXX)
    activate-global-python-argcomplete --dest=- > "${ZENDEV_ARGCOMPLETE}"
    source "${ZENDEV_ARGCOMPLETE}"
    rm -f "${ZENDEV_ARGCOMPLETE}"
fi
