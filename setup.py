#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='afg2225-library',
    version='0.2.0',    
    description='Python library to control arbitrary function generator GW Instek AFG-2225 via USB.',
    url='https://git.bsse.ethz.ch/pruppen/afg2225-library',
    author='Peter Ruppen',
    author_email='peter.ruppen@bsse.ethz.ch',
    license='GNU 3.0',
    packages=['afg2225library'],
    install_requires=['pyvisa', 'pyserial'],

)