#!/usr/bin/env python

from distutils.core import setup
from distutils.command.build import build

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from storrest.gitversion import make_git_version_file


class git_versioned_build(build):
    def run(self):
        make_git_version_file()
        build.run(self)

setup(
    name='storrest',
    version='0.0.1',
    author='Alexei Sheplyakov',
    author_email='asheplyakov@mirantis.com',
    packages=['storrest'],
    description='RESTful storcli wrapper',
    scripts=['bin/storrest'],
    install_requires=["web.py >= 0.35"],
    cmdclass={'build': git_versioned_build},
)
