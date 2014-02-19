======
zendev
======
-------------------------------
The Zenoss Dev Environment Tool
-------------------------------

Zenoss Dev Environment

* Documentation: http://zendev.rtfd.org.

Instructions
--------

* git clone https://github.com/zenoss/zendev.git
* cd zendev
* git checkout develop
* sudo pip install -e .
* echo "source $(zendev bootstrap)" >> ~/.bashrc
    if your macosx /bin/bash is old (older than 4.2), use brew install bash and change your login shell to /usr/local/bin/bash
* source ~/.bashrc
* zendev init europa-dev
* zendev use europa-dev
* cd build/manifests
* zendev add *
* zendev box create --type sourcebuild europa-vm
* zendev sync
* zendev build src
