import os
from setuptools import setup, find_packages

__version__ = os.environ.get('VERSION', None)
if __version__ is None:
    raise ValueError('VERSION environment variable is not set')


if __name__ == '__main__':
    setup(
        name="python-mongodm",
        version=__version__,
        author="Ferréol Jeannot-Lorente",
        description="Asynchronous Python ODM for MongoDB based on Motor",
        packages=find_packages(where='./src'),
        readme="README.md",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        python_requires='>=3.6',
        package_dir={'': 'src'},
        install_requires=['pydantic==1.10.2', "typing-extensions==4.3.0; python_version >= '3.7'"],
        project_urls={
            "Homepage": "https://github.com/tritons-io/MongODM",
            "Bug Tracker": "https://github.com/tritons-io/MongODM/issues"
        }
    )
