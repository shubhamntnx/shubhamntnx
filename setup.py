#!/usr/bin/env python3
"""
Setup script for Nutanix CDP Strict Rack Awareness Test Suite
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="nutanix-cdp-strict-rack-awareness-tests",
    version="1.0.0",
    author="Nutanix CDP Test Team",
    author_email="cdp-test-team@nutanix.com",
    description="Comprehensive test suite for Nutanix CDP strict rack awareness functionality",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nutanix/cdp-strict-rack-awareness-tests",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "strict-ra-tests=testcases.cdp.strict_rack_awareness.test_runner:main",
        ],
    },
    include_package_data=True,
    package_data={
        "testcases.cdp.strict_rack_awareness": ["*.json", "*.md"],
    },
)