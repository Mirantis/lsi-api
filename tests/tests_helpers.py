
import os
import sys


def add_top_srcdir_to_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    top_srcdir = os.path.abspath(os.path.join(script_dir, '..'))
    sys.path.insert(0, top_srcdir)
