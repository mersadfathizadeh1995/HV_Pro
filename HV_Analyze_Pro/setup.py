"""
HVSR Pro Setup Script
=====================

Installation script for the HVSR Pro package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README if it exists
long_description = ""
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text(encoding='utf-8')

setup(
    name="hvsr-pro",
    version="0.2.0",
    author="OSCAR HVSR Development Team",
    description="Professional HVSR Analysis Package for Seismic Site Characterization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/hvsr-pro",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
        "scipy>=1.5.0",
        "matplotlib>=3.3.0",
    ],
    extras_require={
        "gui": [
            "PyQt5>=5.15.0",
        ],
        "seismic": [
            "obspy>=1.2.0",
        ],
        "full": [
            "PyQt5>=5.15.0",
            "obspy>=1.2.0",
            "pydantic>=1.8.0",
        ],
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hvsr-pro=hvsr_pro.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

