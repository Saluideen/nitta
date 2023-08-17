from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in nitta/__init__.py
from nitta import __version__ as version

setup(
	name="nitta",
	version=version,
	description="Nitta",
	author="Ideenkreise",
	author_email="nitta@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
