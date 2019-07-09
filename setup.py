from setuptools import find_packages, setup

version = '1.0.1.dev0'

setup(
    name='access_control',
    version=version,
    long_description="",
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'troposphere',
    ],
    entry_points="""
    [console_scripts]
    accessc = access_control.cli:main
    """
    )
