#!/usr/bin/env python
# Copyright 2014 Avago Technologies Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this software except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
