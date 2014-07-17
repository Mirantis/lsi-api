
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

def patch_subprocess(subprocess):
    if "check_output" not in dir(subprocess):
        print 'patching subprocess module'

        class CalledProcessError(subprocess.CalledProcessError):
            def __init__(self, retcode, cmd, output=None):
                super(CalledProcessError, self).__init__(retcode, cmd)
                self._output = output

            @property
            def output(self):
                return self._output

        subprocess.CalledProcessError = CalledProcessError

        def check_output(*popenargs, **kwargs):
            if 'stdout' in kwargs:
                raise ValueError('stdout argument not allowed, it will be overridden.')
            process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
            output, unused_err = process.communicate()
            retcode = process.poll()
            if retcode:
                cmd = kwargs.get("args")
                if cmd is None:
                    cmd = popenargs[0]
                raise subprocess.CalledProcessError(retcode, cmd, output=output)
            return output

        subprocess.check_output = check_output
