#! /bin/bash
HOST=$(hostname -i)
# Change service variables
echo "Changing Zenoss.cse variables"
for var in $(serviced service variable list Zenoss.cse | grep global.conf.auth0); do serviced service variable unset Zenoss.cse $var; done
serviced service variable set Zenoss.cse global.conf.cse-vhost $HOST
serviced service variable set Zenoss.cse global.conf.cse-virtualroot /cse
serviced service variable set Zenoss.cse cse.project zenoss-zing
serviced service variable set Zenoss.cse cse.tenant acme_corp
serviced service variable set Zenoss.cse cse.source wily_coyote

# Create a script to enable the emulator,
cat << EOF >> /tmp/enable_zing_emulator.sh
#!/bin/bash
sed -i '/^use-emulator.*$/d' \$1
sed -i '/^emulator-host-port.*$/d' \$1
sed -i '/^ *#use-emulator/a use-emulator: true' \$1
sed -i '/^ *#emulator-host-port/a emulator-host-port: $HOST:8085' \$1
EOF
chmod +x /tmp/enable_zing_emulator.sh

# Make edits to zing-connector config
echo "Changing zing-connector config"
serviced service config edit --editor /tmp/enable_zing_emulator.sh zing-connector /opt/zenoss/etc/zing-connector/zing-connector.yml
rm -f /tmp/enable_zing_emulator.sh

# Start the emulator running 
echo "Starting zing-connector emulator on port 8085"
docker run --rm --env CLOUDSDK_CORE_PROJECT=zenoss-zing -p 8085:8085 zenoss/gcloud-emulator:pubsub &
sleep 5
#
# Create a script to enable local logins
cat << EOF >> /tmp/enable_local_login.sh
#!/bin/bash
sed -i '/location ~\* \^\/zport\/acl_users\/cookieAuthHelper\/login/,+3 d' \$1
EOF
chmod +x /tmp/enable_local_login.sh
#
echo "Changing zproxy config to remove disable of local login"
serviced service config edit --editor /tmp/enable_local_login.sh Zenoss.cse /opt/zenoss/zproxy/conf/zproxy-nginx.conf
rm -f /tmp/enable_local_login.sh
#
# Just restart zproxy and zing-connector
echo "Restarting zproxy and zing-connector"
serviced service restart Zenoss.cse --auto-launch=False
serviced service restart zing-connector
