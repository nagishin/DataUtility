# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='DataUtility',
    packages=['DataUtility'],
    version='1.1.14',
    author='Nagi',
    url='https://github.com/nagishin/DataUtility.git',
    install_requires=['requests', 'datetime', 'python-dateutil', 'pytz', 'numpy', 'pandas', 'matplotlib', 'mplfinance', 'japanize-matplotlib', 'seaborn', 'Pillow', 'pybybit @ git+https://github.com/MtkN1/pybybit.git'],
)
