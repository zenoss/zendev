#!/bin/bash

PATH="$GOPATH/bin:$PATH"  # add GOPATH/bin to PATH for root user to find path to serviced

IP=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
EUROPA=$(zendev root)
PRODUCT_TYPE=${PRODUCT_TYPE:-"core"}
TEMPLATE="${EUROPA}/build/services/Zenoss.$PRODUCT_TYPE"
BUILD=${BUILD:-""}
if  [[ -n $BUILD ]]; then
    TEMPLATE="$HOME/zenoss5-${PRODUCT_TYPE}-5.0.0_${BUILD}.json"
    if [[ ! -f "${TEMPLATE}" ]]; then
        wget -O- http://artifacts.zenoss.loc/europa/${BUILD}/$(basename ${TEMPLATE}) | cat >${TEMPLATE}
        set -x
        images=$(awk '/ImageId/ {print $2}' ${TEMPLATE}|sed 's/[",]//g;' | sort -u)
        if [[ -n $images ]]; then
            docker login -u zenossinc+alphaeval -e "alpha2@zenoss.com" -p WP0FHD2M9VIKIX6NUXKTUQO23ZEWNSJLGDBA3SGEK4BLAI66HN5EU0BOKN4FVMFF https://quay.io/v1/
            for image in $images; do
               docker pull $image
            done
        fi
    fi
fi

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
            echo "$(date +'%Y-%m-%d %H:%M:%S'): serviced is ready - performing add-host, add-template, and deploy-template in 6 seconds"
            sleep 6
            break
        fi
        sleep 1
    done

    local cmd=""

    cmd="${SERVICED} add-host $IP:4979 default"
    echo "$(date +'%Y-%m-%d %H:%M:%S'): performing: $cmd"
    $cmd

    cmd="${SERVICED} add-template ${TEMPLATE}"
    echo "$(date +'%Y-%m-%d %H:%M:%S'): performing: $cmd"
    TEMPLATE_ID=$($cmd)

    cmd="${SERVICED} deploy-template ${TEMPLATE_ID} default zenoss"
    echo "$(date +'%Y-%m-%d %H:%M:%S'): performing: $cmd"
    $cmd
    sleep 5

    ZENOSS_ROOT_SERVICE=$(serviced services | awk '/Zenoss/ {print $2; exit}')
    if [ "${BASH_ARGV[0]}" == "startall" ]; then
        echo "$(date +'%Y-%m-%d %H:%M:%S'): performing: ${SERVICED} start-service ${ZENOSS_ROOT_SERVICE}"
        ${SERVICED} start-service ${ZENOSS_ROOT_SERVICE}
    fi
}

deploy &
${SERVICED} -master -agent ${RESETSERVICED_ARGS}

