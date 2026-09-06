"""PyFlumeNG setuptools configuration."""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="PyFlumeNG",
    version="1.0.0",
    author="ChrisMandich",
    author_email="Chris@Mandich.net",
    description="Complete Flume API client with Personal API and portal capabilities",
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/ChrisMandich/PyFlume",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pyjwt",
        "ratelimit",
        "requests",
        'backports.zoneinfo; python_version<"3.9"',
    ],
)
