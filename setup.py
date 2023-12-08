#!/usr/bin/env python
from setuptools import setup

setup(
    name='nameko-sqlalchemy',
    version='1.5.0',
    description='SQLAlchemy dependency for nameko services',
    author='onefinestay',
    author_email='engineering@onefinestay.com',
    url='http://github.com/onefinestay/nameko-sqlalchemy',
    packages=['nameko_sqlalchemy'],
    install_requires=[
        "nameko>=2.0.0",
        "sqlalchemy>=1.4,<2"
    ],
    extras_require={
        'dev': [
            "coverage==7.3.2",
            "isort==5.12.0",
            "pytest>=7.4.3,<8",
            "requests==2.31.0",
            "ruff==0.1.6",
            "PyMySQL==1.1.0",
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
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",

    ]
)
