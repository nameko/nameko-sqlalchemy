#!/usr/bin/env python
from setuptools import setup

setup(
    name='nameko-sqlalchemy',
    version='1.2.0',
    description='SQLAlchemy dependency for nameko services',
    author='onefinestay',
    author_email='engineering@onefinestay.com',
    url='http://github.com/onefinestay/nameko-sqlalchemy',
    packages=['nameko_sqlalchemy'],
    install_requires=[
        "nameko>=2.0.0",
        "sqlalchemy"
    ],
    extras_require={
        'dev': [
            "coverage==4.0.3",
            "flake8==2.5.4",
            "pylint==1.7.5",
            "pytest==2.9.1",
            "requests==2.18.4",
            "PyMySQL",
        ]
    },
    entry_points={
        'pytest11': [
            'nameko_sqlalchemy=nameko_sqlalchemy.pytest_fixtures'
        ]
    },
    zip_safe=True,
    license='Apache License, Version 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ]
)
