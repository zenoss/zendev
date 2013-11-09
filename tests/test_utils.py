#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_utils
----------------------------------

Tests for `utils` module.
"""

import unittest
import tempfile
import py
import json
import subprocess

from zendev.utils import is_git_repo, is_manifest


_MANIFEST = json.dumps({
    'repos': {
        'arepo': {
            'repo': 'iancmcc/dotfiles',
            'ref': 'master'
        }
    } 
})


class TestUtils(unittest.TestCase):

    def run(self, *args, **kwargs):
        self.tempdir = py.path.local(tempfile.mkdtemp())
        try:
            with self.tempdir.as_cwd():
                super(TestUtils, self).run(*args, **kwargs)
        finally:
            self.tempdir.remove()


    def test_is_git_repo(self):
        self.assertFalse(is_git_repo(self.tempdir))
        subprocess.call(["git", "init"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        self.assertTrue(is_git_repo(self.tempdir))
        self.assertFalse(is_git_repo("/not/a/path"))
        fileinrepo = self.tempdir.ensure('something.file')
        self.assertFalse(is_git_repo(fileinrepo))

    def test_is_manifest(self):
        manifest = self.tempdir.join('manifest')

        # Check nonexistent
        self.assertFalse(is_manifest(manifest))

        # Check invalid manifest
        self.tempdir.ensure('manifest')
        manifest.write("NOT A MANIFEST")
        self.assertFalse(is_manifest(manifest))

        # Check valid manifest
        manifest.write(_MANIFEST)
        self.assertTrue(is_manifest(manifest))



if __name__ == '__main__':
    unittest.main()