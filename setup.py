#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.md').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='zendev',
    version='0.2.0',
    description='Zenoss Dev Environment',
    long_description=readme + '\n\n' + history,
    author='Ian McCracken',
    author_email='ian@zenoss.com',
    url='https://github.com/iancmcc/zendev',
    packages=[
        'zendev',
    ],
    package_dir={'zendev': 'zendev'},
    include_package_data=True,
    package_data={'zendev': ['*.sh']},
    install_requires=[
        "gitflow",
        "termcolor",
        "py",
        "argcomplete",
        "tabulate",
        "progressbar2==2.6.0",
        "python-vagrant==0.4.0",
        "jinja2",
        "requests<2.26"
    ],
    dependency_links=['https://github.com/todddeluca/python-vagrant/archive/master.zip#egg=python-vagrant-0.4.2'],
    license="Commercial",
    zip_safe=False,
    keywords='zendev',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    entry_points="""
    [console_scripts]
    zendev = zendev.zendev:main
    """,
)
