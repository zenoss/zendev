#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_zendev
----------------------------------

Tests for `zendev` module.
"""

import unittest
import tempfile
import py

from zendev.environment import init_config_dir, get_config_dir



class TestConfigDir(unittest.TestCase):

    def setUp(self):
        self._tempdir = py.path.local(tempfile.mkdtemp())

    def test_init_config_dir(self):
        """
        Verify that a config dir is initialized.
        """
        with self._tempdir.as_cwd():
            init_config_dir()
        if not self._tempdir.join('.zendev').check():
            self.fail("Directory was not created")

    def test_get_config_dir(self):
        target = self._tempdir.join('.zendev')
        with self._tempdir.as_cwd():
            init_config_dir()
        child = self._tempdir.ensure('child/a/b/c', dir=True)
        with child.as_cwd():
            self.assertEquals(target.realpath(), get_config_dir())


    def tearDown(self):
        self._tempdir.remove()

if __name__ == '__main__':
    unittest.main()