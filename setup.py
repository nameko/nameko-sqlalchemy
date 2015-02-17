#!/usr/bin/env python
from setuptools import setup, find_packages
from os.path import abspath, dirname


setup_dir = dirname(abspath(__file__))

setup(
    name='nameko-sqlalchemy',
    version='0.0.1',
    description='SQLAlchemy dependency for nameko services',
    author='onefinestay',
    author_email='engineering@onefinestay.com',
    url='http://github.com/onefinestay/nameko-sqlalchemy',
    packages=find_packages(exclude=['test']),
    install_requires=[
        "nameko>=2.0.0",
        "sqlalchemy"
    ],
    dependency_links=[],
    zip_safe=True,
    license='Apache License, Version 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ]
)
