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

import os
import subprocess

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if 'check_output' not in dir(subprocess):
    from storcompat import patch_subprocess
    patch_subprocess(subprocess)


def gitdir():
    _gitdir = os.path.join(TOPDIR, '.git')
    return TOPDIR if os.path.isdir(_gitdir) else None


def get_git_version(slen=8):
    repodir = gitdir()
    cmd = 'git rev-parse HEAD'
    if slen:
        cmd = 'git rev-parse --short=%s HEAD' % slen
    try:
        commit_id = subprocess.check_output(cmd.split(),
                                            cwd=repodir).strip()
    except (subprocess.CalledProcessError, OSError):
        commit_id = None
    return commit_id


def make_git_version_file(version_file=None):
    commit_id = get_git_version()
    if version_file is None:
        mydir = os.path.abspath(os.path.dirname(__file__))
        version_file = os.path.join(mydir, 'storversion.py')
    with open(version_file, 'w') as f:
        print >> f, "\nstorrest_git_version = '%s'\n" % commit_id
