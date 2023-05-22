# Motivation
Ability to automate (safely) package upgrade.
Most production projects has all packages in requirements.txt set in `==` Thus meaning that code was developed and tested with a specific package version.
After a while - newer versions of packages become avaialble but mostly ignored - since code is already developed, tested, and works (suposedly). If it works that dont touch it, right...??? Well no... it's wrong!
If the code works - and it gets the job done, why do I care if there is a newer package? right?? WRONG!
See packages are made from code - and code has a tendency to have vulnerabilities. Those vulnerabilities could be expolited. You can chenge your code to be more secure, but what if the vulnerability lies inside a package, or a package that installed by another package? Food for thought.
You can upgrade all your packages by hand, but we belive that tedious tasks shouold be automated.


### Bumper Sticker
You can bump the version - update the version to be one version higher.
You can stick the version - do not update a given version.
Hence the name: BumperSticker.
And yes, we are aware that bs stands for bullshit as well - isn't it ironic.


## Usage:
This tool was designed to be used in pipeline, but its perfectly acceptable to be used manually as well.

<!-- `$ bumpersticker init` - Will generate a cofnig file, if none exists. -->
`$ bumpersticker list` - Will list all your packages and their available upgrades.
`$ bumpersticker bump` - Will check what versions are available for each package and will choose a package - and a new version. will update requirements.txt you cna then `pip3 install -r requirements.txt and then check if it works.

`$ bumpersticker revert` - will revert an upgraded package to its previous version.
**NOTE**: This will work only if you previously ran `$ bumpersticker bump`


### How to use it in pipeline:
Before running tests: do
`$ bumpersticker bump`
It will choose a package that could be upgraded (a newer version is available on pip repository) to a higher version. will update `requirements.txt`
and next time build runs, it will install a newer version of that package. If tests will pass, then everything is OK and its fine to use the newer package.
If tests fail, pipeline should tell bumpersticker to revert that previous change:
`$ bumpersticker revert`
Bumpersticker will know from its own cache which package needs to be reverted. This means that newer version of that package breaks your code. You can add another step to your pipeline to send you an email or slack notification about what happeened (optional).


Bumpersticker will add a `bs-cache` file to your project - you should add it so your source control.

Bumpersticker can receive configuration in the command line, but you can also give it a config file `.bsrc` or `.bsconfrc` or `bsconf.toml` and it will work with it.
Configuration file should be in .toml syntax.
If you pass in options into cli - those options will override the config.


# TOOO:
* When parsing all versions from pip repo - should discard all versions that are with some suffix (rc, alpha, beta)
* Better print progress - when fetching all package versions
* resolve configs.
* bump a version