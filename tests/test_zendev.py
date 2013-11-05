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
import json

from zendev.environment import init_config_dir, get_config_dir, CONFIG_DIR
from zendev.environment import NotInitialized, ZenDevEnvironment


_MANIFEST = json.dumps({
    'repos': {
        'arepo': {
            'repo': 'iancmcc/dotfiles',
            'ref': 'master'
        }
    } 
})


class TestEnvironment(unittest.TestCase):

    def run(self, *args, **kwargs):
        self.tempdir = py.path.local(tempfile.mkdtemp())
        self.cfgdir = self.tempdir.join(CONFIG_DIR)
        try:
            with self.tempdir.as_cwd():
                super(TestEnvironment, self).run(*args, **kwargs)
        finally:
            self.tempdir.remove()

    def test_init_config_dir(self):
        """
        Verify that a config dir is initialized.
        """
        init_config_dir()
        if not self.cfgdir.check():
            self.fail("Directory was not created")

    def test_get_config_dir(self):
        self.assertRaises(NotInitialized, get_config_dir)
        child = self.tempdir.ensure('child/a/b/c', dir=True)
        with child.as_cwd():
            self.assertRaises(NotInitialized, get_config_dir)
        init_config_dir()
        self.assertEquals(self.cfgdir.realpath(), get_config_dir())
        with child.as_cwd():
            self.assertEquals(self.cfgdir.realpath(), get_config_dir())

    def test_config_in_env(self):
        self.assertRaises(NotInitialized, ZenDevEnvironment)
        init_config_dir()
        env = ZenDevEnvironment()
        self.assertEquals(self.cfgdir.realpath(), env._config)

    def test_manifest(self):
        pass


if __name__ == '__main__':
    unittest.main()