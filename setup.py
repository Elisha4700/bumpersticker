from setuptools import setup, find_packages

setup(
    name='bumpersticker',  # Required
    version='0.1.0',
    description='Package ',
    author='Elisha Shapiro <elisha.shaprio@otorio.com>',
    keywords='pip, packages, install, version, bump',  # Optional
    packages=find_packages(),  # Required

    install_requires=[
        'requests>=1.0.1',
        'beautifulsoup4>=3.5.1',
        'cmp_version>=0.7.0',
        'rich>=13.0.0',
    ],

    # entry_points={
    #   'console_scripts': [
    #     'bumpersticker = bumpersticker.__main__'
    #   ]
    # },

    entry_points = '''
        [console_scripts]
        bumpersticker=bumpersticker.__main__:cli
    '''

)
