from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="logistics_system",
	version="0.0.1",
	description="Logistics System - delivery orders, delivery runs, drivers, cash banking",
	author="Backend Task Submission",
	author_email="dev@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
