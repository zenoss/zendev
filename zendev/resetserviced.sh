#!/bin/bash

IP=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
EUROPA=$(zendev root)
SERVICED=$(which serviced)
sudo rm -rf /tmp/serviced*
deploy () {
    sleep 20
    ${SERVICED} add-host $IP:4979 default
    TEMPLATE_ID=$(${SERVICED} add-template ${EUROPA}/build/services/Zenoss/Zenoss)
    ${SERVICED} deploy-template ${TEMPLATE_ID} default zenoss
}
deploy &
serviced -master -agent