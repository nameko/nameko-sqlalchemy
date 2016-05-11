#!/usr/bin/env python
from setuptools import setup

setup(
    name='nameko-sqlalchemy',
    version='0.0.2',
    description='SQLAlchemy dependency for nameko services',
    author='onefinestay',
    author_email='engineering@onefinestay.com',
    url='http://github.com/onefinestay/nameko-sqlalchemy',
    py_modules=['nameko_sqlalchemy'],
    install_requires=[
        "nameko>=2.0.0",
        "sqlalchemy"
    ],
    extras_require={
        'dev': [
            "coverage==4.0.3",
            "flake8==2.5.4",
            "pylint==1.5.5",
            "pytest==2.9.1",
        ]
    },
    dependency_links=[],
    zip_safe=True,
    license='Apache License, Version 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ]
)
