===============================
Zenoss Dev Environment
===============================

.. image:: https://badge.fury.io/py/zendev.png
    :target: http://badge.fury.io/py/zendev
    
.. image:: https://pypip.in/d/zendev/badge.png
        :target: https://crate.io/packages/zendev?version=latest


Zenoss Dev Environment

* Documentation: http://zendev.rtfd.org.

Instructions
--------

* git clone https://github.com/zenoss/zendev.git
* cd zendev
* git checkout develop
* sudo pip install -e .
* echo "source $(zendev bootstrap)" >> ~/.bashrc
* source ~/.bashrc
* zendev init europa-dev
* zendev use europa-dev
* cd build/manifests
* zendev add *
* zendev box create --type sourcebuild europa-vm
* zendev sync
* zendev build src
