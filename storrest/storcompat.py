
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
