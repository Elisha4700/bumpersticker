import os
import click

from typing import List
from requests import request

from bs4 import BeautifulSoup
from cmp_version import VersionString

from .output import print_formated
from .versioning import extract_version_from_label
from .file_utils import get_config_from_file


# TODO: bump version


ctx = dict()

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







def remove_duplicates(versions)-> List[str]:
    vers = set(versions)
    return [v for v in vers]


def get_available_versions(package_name: str, total_packages: int):
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
    except Exception as e:
        print('something went wronfg while getting liist of verisons.')
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


def parse_line(line: str) -> dict:
    line = line.strip()

    if ctx.get("debug"):
        print(f"parsing line:")
        print(line)

    if "#" in line and line.index("#") == 0:  # comment line
        if ctx.get("debug"):
            print(f"comment... moving on")
        return

    if len(line) == 0:  # empty line
        return

    op = extract_op(line.strip())
    parts = [part.strip() for part in line.split(op)]
    return {"package_name": parts[0], "current_version": parts[1], "op": op}


def parse_requirements():
    with open(get_requirements_file()) as f:
        lines = f.readlines()
        for line in lines:
            if ctx.get("debug"):
                print(f"line: {line}")

            package = parse_line(line)

            if not package:
                continue

            pkg_name = package.get("package_name")
            versions = get_available_versions(package_name=pkg_name, total_packages=len(lines))

            ctx["packages"][pkg_name] = package
            ctx["packages"][pkg_name]["versions"] = versions

            v = package.get("current_version")
            if v in versions:
                current_v_index = versions.index(v)

                ctx["packages"][pkg_name]["versions"] = versions
                # ctx["packages"][pkg_name]["lower_versions"] = versions[0:current_v_index]
                ctx["packages"][pkg_name]["higher_versions"] = versions[current_v_index + 1:]






@click.group()
def bs():
    """bs for BumperSticker - and yes, we are aware it stands also for Bullshit - how ironic!"""
    pass


@bs.command()
@click.option("--index", default="https://pypi.org/simple/", help="pypi index url.")
@click.option("-d", "--debug", type=bool, default=False, help="print debugging information")  # https://click.palletsprojects.com/en/8.1.x/options/#boolean-flags
@click.option("-o", "--out", default="cli", type=str, help="Output format")
def list(index="https://pypi.org/simple/", debug=False, out="cli"):
    ctx["cwd"] = os.getcwd()

    config = get_config_from_file(ctx=ctx)
    cli_context = dict()

    ctx["index"] = config.get("index", index)
    ctx["debug"] = debug
    ctx["out"] = out
    ctx["packages"] = {}

    if not check_if_requirements_exists():
        print(f"Could not find `requirements.txt` file in current dierctory: {ctx.get('cwd')}.")
    else:
        if ctx.get("debug"):
            print(ctx)



        parse_requirements()
        print_formated(ctx=ctx)

@bs.command()
def bump():
    print('Command Bump')

cli = click.CommandCollection(sources=[bs])

cli()