#!/usr/bin/env python

from distutils.core import setup

setup(
    name='storrest',
    version='0.0.1',
    author='Alexei Sheplyakov',
    author_email='asheplyakov@mirantis.com',
    packages=['storrest'],
    description='RESTful storcli wrapper',
    scripts=['bin/storrest'],
    install_requires=["web.py >= 0.35"],
)
