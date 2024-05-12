import os
import time
import click


from typing import List, Union
from requests import request
from rich.progress import Progress

from bs4 import BeautifulSoup
from cmp_version import VersionString

from .package_version import PackageVersion
from .output import print_formated
from .versioning import extract_version_from_label
from .file_utils import get_config_from_file
from .const import (
    DEFAULT_OUT_FORMAT,
    DEFAULT_DEBUG,
    PIP_DEFAULT_INDEX,
    BS_DEFAULT_OUTPUT,
)

# TODO: bump version

CWD = os.getcwd()
ctx = dict()


def pretty_print_context(ctx: dict) -> None:
    print('<<<<<<<<<<<<<<<< CTX >>>>>>>>>>>>>>>>>>>')
    for key, val in ctx.items():
        print(f"{key}: {val}")

    print('<<<<<<<<<<<<<< END - CTX >>>>>>>>>>>>>>>>>')


def pad(max_len: int, value: str) -> str:
    pad_by = max_len - len(value)
    if pad_by > 0:
        return f"{' ' * pad_by}{value}"

    return value


def get_page_content(package_name: str) -> str:
    try:
        url = f"{ctx.get('index')}{package_name}"

        if ctx.get("debug"):
            print(f"fetching: {package_name}      {url}")

        resp = request(method="GET", url=url)

        return resp.text
    except Exception as err:
        print(f"Failed to get data for package {package_name}.")
        print(err)
        return None


def remove_duplicates(versions) -> List[str]:
    vers = set(versions)
    return [v for v in vers]


def get_available_versions(package_name: str):
    try:
        versions = []
        page_content = get_page_content(package_name=package_name)

        soup = BeautifulSoup(page_content, "html.parser")
        a_tags = soup.find_all("a")

        available_packages = [a.get_text() for a in a_tags]

        if ctx.get("debug"):
            print("available_packages", available_packages)

        versions = [
            extract_version_from_label(text=p, package_name=package_name)
            for p in available_packages
        ]

        unique_versions = remove_duplicates(versions=versions)
        unique_versions = sorted(unique_versions, key=VersionString)

        if ctx.get("debug"):
            print("versions")
            print(unique_versions)

        return unique_versions
    except Exception as err:
        print("something went wronfg while getting liist of verisons.", err)
        return []


def get_requirements_file():
    """
    Will return the requirements.txt file based on context:
    directory and the given reuqirements file name
    """
    return f"{ctx.get('cwd')}/requirements.txt"


def check_if_requirements_exists():
    return os.path.exists(get_requirements_file())


def extract_op(line: str) -> str:
    ops = [">", "<", "<=", ">=", "==", "!=", "~="]
    for op in ops:
        if line.find(op) >= 0:
            return op


# def parse_line(line: str) -> dict:
#     try:
#         line = line.strip()

#         if ctx.get("debug"):
#             print(f"parsing line:")
#             print(line)

#         if "#" in line and line.index("#") == 0:  # comment line
#             if ctx.get("debug"):
#                 print(f"comment... moving on")
#             return

#         if len(line) == 0:  # empty line
#             return

#         op = extract_op(line.strip())
#         parts = [part.strip() for part in line.split(op)]
#         return {"package_name": parts[0], "current_version": parts[1], "op": op}
#     except Exception as e:
#         print(f'Could not parse line: {line}')
#         print(e)
#     finally:
#       return {}


def pull_verions_for_packages() -> None:
    with Progress() as progress:
        total = len(ctx.get("packages").items())
        task_id = None
        step = (1 / (total if total else 1)) * 100

        if ctx.get('debug'):
            print("Step", step)

        task_id = progress.add_task(
            "Pulling: ", total=total, start=True, visible=False
        )

        package_names = ctx.get("packages").keys()
        pkg_max_len = max([len(p) for p in package_names])

        index = 0
        while not progress.finished:
            for package_name, package in ctx.get("packages").items():
                if "versions" not in ctx["packages"][package_name]:
                    progress.update(task_id,
                                    visible=True,
                                    description=f"Pulling {pad(max_len=pkg_max_len, value=package_name)}")
                    versions = get_available_versions(
                        package_name=package_name)
                    time.sleep(0.1)
                    progress.advance(task_id)
                    index += 1

                    ctx["packages"][package_name]["versions"] = versions
                    v = package.get("current_version")
                    if v in versions:
                        current_v_index = versions.index(v)

                        ctx["packages"][package_name]["versions"] = versions
                        ctx["packages"][package_name]["higher_versions"] = versions[
                            current_v_index + 1:
                        ]
            progress.update(task_id, completed=True, visible=False)


def parse_requirements(ctx: dict) -> None:
    # import pdb
    with open(get_requirements_file()) as f:

        print(f'Reading requiremets file: {get_requirements_file()}')

        lines = f.readlines()
        for line in lines:
            package = PackageVersion(line=line, ctx=ctx)
            print(f'---  Line: {package.line}')

            # pdb.set_trace()

            if package.is_error or package.is_empty or package.is_comment:
                continue

            pkg_name = package.package_name
            ctx["packages"][pkg_name] = {
                "package_name": package.package_name,
                "current_version": package.current_version,
                "op": package.operand,
            }


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


def resolve_config(cli_args: dict, conf: dict) -> dict:
    """
    Receives arguments passed into cli, configuration file, 
    and resolves them to context.
    cli args - are strongest and will overrride same param from config file.
    If no argument is passed - will take one from config file.
    If there is no argument in config - will use a default.

    Will update global ctx.
    """

    ctx["index"] = resolve_value(
        cli_args.get("index"), conf.get("index"), PIP_DEFAULT_INDEX
    )
    ctx["debug"] = resolve_value(
        cli_args.get("debug"), conf.get("debug"), DEFAULT_DEBUG
    )
    ctx["out"] = resolve_value(cli_args.get(
        "out"), conf.get("out"), DEFAULT_OUT_FORMAT)
    ctx["packages"] = {}
    return ctx


def build_context(
        index: str = PIP_DEFAULT_INDEX,
        debug: bool = False,
        out: str = BS_DEFAULT_OUTPUT
):
    ctx["cwd"] = os.getcwd()
    config = get_config_from_file(ctx=ctx)
    return resolve_config(cli_args=dict(index=index, debug=debug, out=out),
                          conf=config)


@click.group()
def bs():
    """bs for BumperSticker - and yes, 
    we are aware it stands also for Bullshit - how ironic!"""
    pass


@bs.command()
@click.option("--index", default=PIP_DEFAULT_INDEX, help="pypi index url.")
@click.option(
    "-d", "--debug", is_flag=True, default=False, help="print debugging information"
)
@click.option("-o", "--out", default=BS_DEFAULT_OUTPUT, type=str, help="Output format")
def list(index: str = None, debug: bool = None, out: str = None) -> None:
    build_context(index, debug, out)
    print("Context resolveds: ", ctx)

    if not check_if_requirements_exists():
        print(
            f"Could not find `requirements.txt` file in current dierctory: {CWD}.")
    else:
        if ctx.get("debug"):
            pretty_print_context(ctx=ctx)

        parse_requirements(ctx=ctx)

        print_formated(ctx=ctx)

        pull_verions_for_packages()


@bs.command()
def config():
    ctx = build_context()
    print_formated(ctx=ctx)


@bs.command()
@click.option("--index", default=PIP_DEFAULT_INDEX, help="pypi index url.")
@click.option(
    "-d", "--debug", is_flag=True, default=False, help="print debugging information"
)
@click.option("-o", "--out", default="cli", type=str, help="Output format")
@click.option("-p", "--package", type=str, help="Pckage name - to be bumped")
def bump(
    index: str = None,
    debug: bool = None,
    out: str = None,
    package: str = None
) -> None:
    build_context(index, debug, out)

    print("Context resolveds: ", ctx)

    print(f"Command Bump: {package}")

    if not check_if_requirements_exists():
        print(
            f"Could not find `requirements.txt` file in current dierctory: {CWD}.")
        return

    if ctx.get("debug"):
        print(ctx)

    parse_requirements()

    if package not in ctx.get("packages", {}).keys():
        print(
            'Package you have requested: "{package}" is not fond in requirements.txt file.'
        )
        return

    pkg_dict = ctx.get("packages", {}).get(package)
    versions = get_available_versions(package_name=package)
    v = pkg_dict.get("current_version")
    print(pkg_dict)
    if v in versions:
        current_v_index = versions.index(v)
        higher_versions = versions[current_v_index + 1:]
        print(higher_versions)
        next_v = higher_versions[0]
        print(f'Bumping {package} ({v}) --> to version: {next_v}')
    else:
        print(f'Could not locate current version of {
              package} in all available versions for this package.')


cli = click.CommandCollection(sources=[bs])


cli()
