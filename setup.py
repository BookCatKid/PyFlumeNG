"""PyFlumeNG setuptools configuration."""

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="PyFlumeNG",
    version="0.12.0",
    author="ChrisMandich",
    author_email="Chris@Mandich.net",
    description="Complete Flume API client with Personal API and portal capabilities",
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/BookCatKid/PyFlumeNG",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    package_data={"pyflumeng": ["py.typed"]},
    include_package_data=True,
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    license="MIT",
    install_requires=[
        "pyjwt",
        "ratelimit",
        "requests",
        'backports.zoneinfo; python_version<"3.9"',
    ],
)
