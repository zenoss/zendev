#!/bin/bash

PATH="$GOPATH/bin:$PATH"  # add GOPATH/bin to PATH for root user to find path to serviced

IP=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
EUROPA=$(zendev root)
SERVICED=$(which serviced)
sudo rm -rf /tmp/serviced*
deploy () {
    # give serviced a little time to startup
    sleep 20

    # wait until serviced is ready - this is necessary on slow VMs
    while true; do
        if ! pgrep -fl "${SERVICED} -master" >/dev/null; then
            echo "serviced is not running - will not add-host nor deploy-template"
            return
        fi
        wget localhost:8787 &>/dev/null
        if [[ 0 == $? ]]; then
            echo "$(date +'%Y-%m-%d %H:%M:%S'): serviced is ready - performing add-host and deploy-template in 6 seconds"
            sleep 6
            break
        fi
        sleep 1
    done

    echo "$(date +'%Y-%m-%d %H:%M:%S'): performing add-host and deploy-template"
    ${SERVICED} add-host $IP:4979 default
    TEMPLATE_ID=$(${SERVICED} add-template ${EUROPA}/build/services/Zenoss)
    ${SERVICED} deploy-template ${TEMPLATE_ID} default zenoss
}
deploy &
${SERVICED} -master -agent ${RESETSERVICED_ARGS}

