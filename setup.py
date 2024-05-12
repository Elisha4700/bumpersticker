from setuptools import setup, find_packages

setup(
    name='bumpersticker',
    version='0.1.0',
    description='Package ',
    author='Elisha Shapiro <elisha.shaprio@otorio.com>',
    keywords='pip, packages, install, version, bump',
    packages=find_packages(),

    install_requires=[
        'requests>=1.0.1',
        'beautifulsoup4>=3.5.1',
        'cmp_version>=0.7.0',
        'rich>=13.0.0',
        'click>=8.1.7',
        'toml>=0.10.2',
    ],

    entry_points = '''
        [console_scripts]
        bs=src.__main__:cli
    ''',
)
