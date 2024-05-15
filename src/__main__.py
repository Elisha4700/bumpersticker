import aiohttp
import asyncio
import click
import json
import logging
import os
import ssl
from typing import Any, List, Union, Optional, Tuple

# from requests import request
# from rich.progress import Progress

from bs4 import BeautifulSoup
from cmp_version import VersionString

from .package_version import PackageVersion
from .output import print_formated
from .versioning import extract_version_from_label
from .file_utils import get_config_from_file


logger = logging.getLogger()
logger.setLevel(level=logging.INFO)


DEFAULT_OUT_FORMAT = "cli"
DEFAULT_DEBUG = False
PIP_DEFAULT_INDEX = "https://pypi.org/simple/"
BS_DEFAULT_OUTPUT = "cli"
BS_CACHE_FILE_NAME = '.bs_cache.yaml'
BUMP_CACHE_KEY = "bump"
STICK_CACHE_KEY = "stick"
TESTING_CACHE_KEY = "testing"


"""
.bs_cache file structure:

{
  "testing": {
    "package_name": "the-name-of-the-package",
    "from_version": "1.1.0",
    "to_version": "1.2.0"
  },

  "sticked_packages": {
    "some_package_that_is_sticked": {
      "package_name": "some_package_that_is_sticked",
      "version": "2.5.1",
    },

    "another_package_that_is_sticked": {
      "package_name": "another_package_that_is_sticked",
      "version": "7.7.0",
    }
  },

  "packages": { // this is the cached packages and all their available versions.

  }

}
"""


CWD = os.getcwd()
ctx: dict[str, Any] = {}


def get_cache() -> dict:
    cache_data: dict = {}
    file_path: str = os.path.join(CWD, BS_CACHE_FILE_NAME)

    if not os.path.exists(file_path):
        logging.debug("Could not find a cache file - returning an empty cache: ")
        return cache_data

    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            if isinstance(data, dict):
                cache_data = data
    except Exception as err:
        logging.exception(err)
    finally:
        return cache_data


def write_cache(cache: dict[Any, Any]) -> None:
    file_path = os.path.join(CWD, BS_CACHE_FILE_NAME)
    with open(file_path, 'w+') as file:
        file.write(json.dumps(cache, indent=4))


def add_package_to_testing_state(
    package_name: str,
    from_version: str,
    to_version: str
) -> None:
    cache = get_cache()
    if cache.get("testing"):
        logging.warning("There is already package in 'Testing' state")
        return

    cache["testing"] = {
        "package_name": package_name,
        "from_version": from_version,
        "to_version": to_version
    }
    write_cache(cache=cache)


def update_package_version_in_requirements_file(
    package_name: Optional[str] = None,
    package_version: Optional[str] = None
) -> None:
    requirements_parsed_lines = parse_requirements()

    req_file = get_requirements_file()

    logging.debug(f"req file: {req_file}")

    with open(req_file, "w") as f:
        for package in requirements_parsed_lines:
            line = package.line
            if package.package_name == package_name:
                line = f"{package.package_name}=={package_version}\n"
            f.write(line)
            logging.debug(f"Write: {line}")


def print_package_versions(package_versions: List[PackageVersion]) -> None:
    for pack_v in package_versions:
        if not (pack_v.is_empty or pack_v.is_comment or pack_v.is_error):
            logging.debug(f'Package version: {pack_v.package_name} -> {pack_v.current_version}')


def pretty_print_context(ctx: dict) -> None:
    print('<<<<<<<<<<<<<<<< CTX >>>>>>>>>>>>>>>>>>>')
    for key, val in ctx.items():
        print(f"{key}: {val}")
    print('<<<<<<<<<<<<<< END - CTX >>>>>>>>>>>>>>>>>')


def is_package_in_testing(package_name: str) -> bool:
    cache = get_cache()
    testing_package_name = cache.get(TESTING_CACHE_KEY, {}).get("package_name")
    return testing_package_name == package_name


def resolve_next_package_to_upgrade(
    packages: dict[str, dict[str, str]]
) -> Optional[dict[str, str]]:
    for package_name, pack in packages.items():
        if not is_package_in_testing(package_name=package_name):
            if pack.get("current_version") and len(pack.get("higher_versions", [])) > 0:
                return {"package_name": package_name,
                        "from_version": str(pack.get("current_version")),
                        "to_version": str(pack.get("higher_versions", [])[0])}

    return None


def pad(max_len: int, value: str) -> str:
    pad_by = max_len - len(value)
    if pad_by > 0:
        return f"{' ' * pad_by}{value}"

    return value

async def fetch(session, url):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with session.get(url, ssl=ssl_context) as response:
        return await response.text()


async def get_page_content(package_name: str) -> str:
    try:
        url = f"{ctx.get('index')}{package_name}"
        logging.debug(f"fetching: {package_name}  -->  {url}")
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, url)
            logging.debug(f"html for: '{package_name}' fetched")
            return html
    except Exception as err:
        logging.exception(f"Failed to get data for package {package_name}.", err)
        return ""


def remove_duplicates(versions) -> List[str]:
    vers = set(versions)
    return [v for v in vers]


async def get_available_versions(package_name: str) -> Tuple[str, List[str]]:
    try:
        versions = []
        page_content = await get_page_content(package_name=package_name)

        soup = BeautifulSoup(page_content, "html.parser")
        a_tags = soup.find_all("a")

        available_packages = [a.get_text() for a in a_tags]

        versions = [
            extract_version_from_label(text=p, package_name=package_name)
            for p in available_packages
        ]

        unique_versions = remove_duplicates(versions=versions)
        unique_versions = sorted(unique_versions, key=VersionString)

        return package_name, unique_versions
    except Exception as err:
        print("something went wronfg while getting liist of verisons.", err)
        return package_name, []


def get_requirements_file():
    """
    Will return the requirements.txt file based on context:
    directory and the given reuqirements file name
    """
    return f"{ctx.get('cwd')}/{ctx.get('req_file')}"


def check_if_requirements_exists():
    return os.path.exists(get_requirements_file())


def ensure_runnin_within_requirements_path() -> None:
    if not check_if_requirements_exists():
        raise Exception(f"""
            Current directory: {os.getcwd()} does not have a requirements.txt file
            - seems like this is not a project root.
            """)


def extract_op(line: str) -> Optional[str]:
    ops = [">", "<", "<=", ">=", "==", "!=", "~="]
    for op in ops:
        if line.find(op) >= 0:
            return op
    return None


async def pull_verions_for_packages(packages: dict[str, dict[str, str]]) -> Any:
    available_versions = {}
    async_tasks = []
    for package_name, _ in packages.items():
        async_tasks.append(get_available_versions(package_name=package_name))

    results = await asyncio.gather(*async_tasks)

    # logging.info("Results")
    # logging.info(results)

    for result in results:
        try:
            package_name, versions = result
            current_version: str = packages.get(package_name, {}).get("current_version", "")
            current_v_index: int = versions.index(current_version)

            if current_v_index == -1:
                logging.warning(
                    f"""
                    Could not find current version: {current_version}
                    for package: {package_name}
                    """
                )
                current_v_index = 0

            available_versions[package_name] = {
                "package_name": package_name,
                "current_version": current_version,
                # "versions": versions,
                "higher_versions": versions[current_v_index + 1:]
            }

        except Exception as err:
            logging.warning(
                f"""
                Could not find current version: {current_version}
                for package: {package_name}
                """
            )
            available_versions[package_name] = {
                "package_name": package_name,
                "versions": [],
                "higher_versions": []
            }

    return available_versions


def parse_requirements() -> List[PackageVersion]:
    try:
        req_file_lines: List[PackageVersion] = []

        with open(get_requirements_file()) as f:
            lines = f.readlines()

            for line in lines:
                package = PackageVersion(line=line, ctx=ctx)
                req_file_lines.append(package)

        # TODO: check if operands are not `==` and suggest to pip freeze.

        return req_file_lines
    except Exception as err:
        print(f"ERROR :: occurred while parsing the {ctx.get('req_file')} file: ", err)
        return []


def package_versions_to_dict(package_list: List[PackageVersion]) -> dict[str, dict[str, str]]:
    result = {}

    for package in package_list:
        if package.is_error or package.is_empty or package.is_comment:
            continue

        result[package.package_name] = {
            "package_name": package.package_name,
            "current_version": package.current_version,
            "op": package.operand,
        }

    return result


def resolve_value(
    cli: Union[str, bool],
    conf: Union[str, bool],
    default: Union[str, bool]
) -> Union[str, bool]:
    if cli:
        return cli

    if conf:
        return conf

    return default


def resolve_config(cli_args: dict[str, Any], conf: dict[str, Any]) -> dict:
    """
    Receives arguments passed into cli, configuration file,
    and resolves them to context.
    cli args - are strongest and will overrride same param from config file.
    If no argument is passed - will take one from config file.
    If there is no argument in config - will use a default.

    Will update global ctx.
    """

    ctx["index"] = resolve_value(
        cli_args.get("index", False), conf.get(
            "index", False), PIP_DEFAULT_INDEX
    )
    ctx["debug"] = resolve_value(
        cli_args.get("debug", False), conf.get("debug", False), DEFAULT_DEBUG
    )
    ctx["out"] = resolve_value(cli_args.get(
        "out", ""), conf.get("out", ""), DEFAULT_OUT_FORMAT)
    ctx["packages"] = {}
    return ctx


def build_context(
    index: str = PIP_DEFAULT_INDEX,
    debug: bool = False,
    out: str = BS_DEFAULT_OUTPUT
):
    ctx["cwd"] = os.getcwd()
    ctx["req_file"] = "requirements.txt"
    config: dict[str, Any] = get_config_from_file(ctx=ctx)
    return resolve_config(cli_args=dict(index=index, debug=debug, out=out),
                          conf=config)


@click.group()
def bs():
    """
    bs for BumperSticker - and yes,
    we are aware it stands also for Bullshit - how ironic!
    """
    pass


@bs.command()
@click.option(
    "--index",
    default=PIP_DEFAULT_INDEX,
    help="pypi index url.",
)
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="print debugging information",
)
@click.option(
    "-o",
    "--out",
    default=BS_DEFAULT_OUTPUT,
    type=str,
    help="Output format",
)
def list(index: str = "", debug: bool = False, out: str = "") -> None:
    if debug:
        logger.setLevel(level=logging.DEBUG)

    build_context(index, debug, out)
    cache = get_cache()

    ###########################################################
    logging.debug("Cache: ")
    logging.debug(cache)
    logging.debug("Context resolveds: ")
    logging.debug(ctx)
    ###########################################################

    if not check_if_requirements_exists():
        logging.warning(
            f"Could not find `{ctx.get('req_file')}` file in current dierctory: {CWD}.")
    else:
        if ctx.get("debug"):
            pretty_print_context(ctx=ctx)

        package_versions = parse_requirements()
        packages = package_versions_to_dict(package_list=package_versions)

        #########################################3
        logging.debug("Packages to dict")
        logging.debug(packages)
        #########################################3

        print_formated(ctx=ctx)

        asyncio.run(pull_verions_for_packages(packages=packages))

        cache = get_cache()
        cache["packages"] = ctx.get("packages")
        write_cache(cache=cache)
        print(cache)


@bs.command()
def config() -> None:
    ctx = build_context()
    print_formated(ctx=ctx)


@bs.command()
@click.option(
    "-i",
    "--index",
    default=PIP_DEFAULT_INDEX,
    help="pypi index url."
)
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="print debugging information"
)
@click.option(
    "-o",
    "--out",
    default="cli",
    type=str,
    help="Output format"
)
# @click.option("-p", "--package", type=str, help="Pckage name - to be bumped")
def bump(
    index: str = "",
    debug: bool = False,
    out: str = "",
    package: str = ""
) -> None:
    if debug:
        logger.setLevel(level=logging.DEBUG)

    build_context(index, debug, out)

    ###############################################
    logging.debug("Context resolveds: ")
    logging.debug(ctx)
    logging.debug(f"Command Bump: {package}")
    ###############################################

    if not check_if_requirements_exists():
        print(
            f"Could not find `{ctx.get('req_file')}` file in current dierctory: {CWD}.")
        return

    package_versions = parse_requirements()
    packages = package_versions_to_dict(package_list=package_versions)

    packages = asyncio.run(pull_verions_for_packages(packages=packages))

    logging.debug("async_result:")
    logging.debug(packages)

    # Store the newly    npackages in cache.
    cache = get_cache()
    cache["packages"] = packages
    write_cache(cache=cache)

    package_to_test = resolve_next_package_to_upgrade(packages=packages)

    if package_to_test is None:
        logging.warn("Cannot fins a package to bump.")
        return

    ##################################################
    logging.debug("package_to_test: ")
    logging.debug(package_to_test)
    ##################################################

    cache[TESTING_CACHE_KEY] = package_to_test
    write_cache(cache=cache)
    update_package_version_in_requirements_file(package_name=package_to_test.get("package_name"),
                                                package_version=package_to_test.get("to_version"))


@bs.command()
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="print debugging information"
)
def ok(debug: bool = False) -> None:
    if debug:
        logger.setLevel(level=logging.DEBUG)

    cache = get_cache()
    package_in_test = cache.get(TESTING_CACHE_KEY, None)

    if package_in_test is None:
        logging.debug("Testing package was not found in cache. Nothing to do...")
        return

    if BUMP_CACHE_KEY not in cache:
        cache[BUMP_CACHE_KEY] = {}

    cache[BUMP_CACHE_KEY][package_in_test.get("package_name")] = package_in_test
    del cache[TESTING_CACHE_KEY]

    write_cache(cache=cache)


@bs.command()
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="print debugging information"
)
def stick(debug: bool = False) -> None:
    if debug:
        logger.setLevel(level=logging.DEBUG)

    build_context(debug=debug)

    cache = get_cache()
    package_in_test = cache.get(TESTING_CACHE_KEY, None)

    if package_in_test is None:
        logging.debug("Testing package was not found in cache. Nothing to do...")
        return

    if STICK_CACHE_KEY not in cache:
        cache[STICK_CACHE_KEY] = {}

    update_package_version_in_requirements_file(
        package_name=package_in_test.get("package_name"),
        package_version=package_in_test.get("from_version"),
    )

    cache[STICK_CACHE_KEY][package_in_test.get("package_name")] = package_in_test
    del cache[TESTING_CACHE_KEY]

    write_cache(cache=cache)


cli = click.CommandCollection(sources=[bs])


# Utils functions:
# - Parse requirements.txt file: will go over all the lines in a given requirements.txt file and will return a list of parsed lines.
# - Get Cache: gets contents of a dictionary file: as dict
# - Write Cache: receives a dict and writes it into a file (.bs_cache)
# - Write requirements.txt file: should override a specific package with a specific version


# List:
#  1. Parse requirements.txt extract all packages.
#  2. Fetch available versions for all the packages.
#  3. Print pretty table of the current status.


# Bump:
#  * Parse requirements.txt extract all packages.
#  * Check if all packages are in cache
#     ** if not:
#          *** Fetch available versions for all the packages.
#          *** rebuild cache
#  * Determine the next package to be updated (from the list of all packages)
#  * Write "testing" package to cache
#  * Update the testing package version in the requirements.txt


# OK:
#  1. Remove the "testing" section in cache file.


# Stick:
#  1. Update the testing package version in the requirements.txt
#  2. Remove the "testing" section in cache file.


cli()
