
import json
import os
import sys


class MultiReturnValues(object):
    """Return different values on subsequent calls of the mock'ed object

    It looks like the documented way to achive this, i.e.
    mocked_object.side_effect = [1, 2, 3]
    does not work properly, hence this hack
    """
    def __init__(self, retvals=None):
        self.calls = -1
        self.retvals = retvals
        self.max_calls = len(retvals)

    def __call__(self, arg):
        self.calls = self.calls + 1
        if self.calls >= self.max_calls:
            raise ValueError('Too many calls: %s, expected <= %s' %
                             (self.calls, self.max_calls))
        return self.retvals[self.calls]

def add_top_srcdir_to_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    top_srcdir = os.path.abspath(os.path.join(script_dir, '..'))
    sys.path.insert(0, top_srcdir)


def read_expected(name, raw=True):
    script_dir = os.path.abspath(os.path.dirname(__file__))
    filename = os.path.join(script_dir, name)
    with open(filename, 'r') as f:
        txt = '\n'.join((l for l in f))
        return txt if raw else json.loads(txt)
