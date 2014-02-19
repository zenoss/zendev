======
zendev
======
-------------------------------
The Zenoss Dev Environment Tool
-------------------------------

* Full Docs: http://jenkins.zendev.org/job/zendev-docs/Zendev_Documentation

zendev takes care of setting up and managing the disparate components of a standard Zenoss development environment, with or without the control plane. It includes:
 * Add GitHub repositories to your source environment
 * Export manifest of source environment (including current branches) for build or import into other zendev environment
 * Quickly view of branches across some or all repositories
 * Perform arbitrary actions across some or all repositories
 * Manage git-flow-based workflow -- create pull requests automatically across multiple repositories
 * Set up and switch between multiple zendev environments on the same box
 * Vagrant box management -- automatically add your SSH keys, mount your source tree, and set up an identical zendev environment
 * Pre-built Vagrant boxes for both RM source build and control plane scenarios

Please feel free to fork and submit pull requests for this project.
