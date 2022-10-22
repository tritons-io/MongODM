import os
from setuptools import setup, find_packages

__version__ = os.environ.get('VERSION')
if __version__ is None:
    raise ValueError('VERSION environment variable is not set')


if __name__ == '__main__':
    setup(
        name="python-mongodm",
        version=__version__,
        author="Ferréol Jeannot-Lorente",
        description="Asynchronous Python ODM for MongoDB based on Motor",
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        packages=find_packages(where='./src'),
        readme="README.md",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        python_requires='>=3.6',
        package_dir={'': 'src'},
        install_requires=['bson==0.5.10', 'motor==3.0.0', 'pydantic==1.10.2', "pymongo==4.2.0; python_version >= '3.7'", "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", "typing-extensions==4.3.0; python_version >= '3.7'"],
        project_urls={
            "Homepage": "https://github.com/tritons-io/MongODM",
            "Bug Tracker": "https://github.com/tritons-io/MongODM/issues"
        }
    )
