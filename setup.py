# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='DataUtility',
    packages=['DataUtility'],
    version='1.0.1',
    author='Nagi',
    url='https://github.com/nagishin/DataUtility.git',
    install_requires=['requests', 'datetime', 'pytz', 'numpy', 'pandas', 'pybybit @ git+https://github.com/MtkN1/pybybit.git'],
)
