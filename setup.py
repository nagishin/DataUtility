# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='DataUtility',
    packages=['DataUtility'],
    version='2.0.0',
    author='Nagi',
    url='https://github.com/nagishin/DataUtility.git',
    install_requires=['requests', 'datetime', 'pytz', 'numpy', 'pandas', 'pybybit'],
    dependency_links=['git+https://github.com/MtkN1/pybybit.git@master#egg=pybybit-2.0.0'],
)
