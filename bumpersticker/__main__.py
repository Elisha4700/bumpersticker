import os
import re
import click

from typing import List
from requests import request
from pathlib import Path
from bs4 import BeautifulSoup
from collections import OrderedDict
from cmp_version import VersionString


ctx = dict()
reg_v = re.compile("\d.\d")


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


def is_prebuit(file_name: str):
    file_extension = Path(file_name).suffix
    return file_extension == ".whl" or file_extension == ".egg"


def extract_version_from_label(text: str, package_name: str) -> str:
    text = text.lower()
    package_name = package_name.lower()

    if is_prebuit(text):
        package_name = package_name.replace("-", "_")

    text = text.replace(f"{package_name}-", "")
    v = (
        text.split("-")[0]
        .replace(".tar.gz", "")
        .replace(".win32.exe", "")
        .replace(".zip", "")
    )
    return v


def remove_duplicates(versions)-> List[str]:
    """
    Simpler version of this would be: list(set(versions)) - but it keeps failing when it runs.
    """
    vers = set(versions)
    return [v for v in vers]
    # versions_dict = dict()

    # for v in versions:
    #     versions_dict[v] = None

    # return list(versions_dict.keys())


def get_available_versions(package_name: str):
    try:
        versions = []
        page_content = get_page_content(package_name=package_name)

        # if ctx.get('debug'):
        #     print(page_content)

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
        # versions = list(set(versions))
        # versions = list(OrderedDict.fromkeys(versions))

        if ctx.get("debug"):
            print("versions")
            print(unique_versions)

        # try:
        #     versions = list(set(sorted(versions)))
        #     if ctx.get('debug'):
        #         print('versions', versions)

        # except Exception as e:
        #     if ctx.get('debug'):
        #         print('Error while sorting options', e)

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
            versions = get_available_versions(package_name=pkg_name)

            ctx["packages"][pkg_name] = package
            ctx["packages"][pkg_name]["versions"] = versions

            v = package.get("current_version")
            if v in versions:
                current_v_index = versions.index(v)

                ctx["packages"][pkg_name]["versions"] = versions
                ctx["packages"][pkg_name]["lower_versions"] = versions[0:current_v_index]
                ctx["packages"][pkg_name]["higher_versions"] = versions[current_v_index + 1:]


def print_formated():
    if ctx.get("out") == "json":
        print(ctx)
        return

    # output for cli
    packages = ctx.get("packages")
    for package_name, package in packages.items():
        op = package.get("op", "????")
        v = package.get("current_version", "????")
        hv = package.get("higher_versions", [])
        print(f"{package_name} {op} {v}         ", hv)


@click.command()
def list():
    print("Command List!")


@click.command()
@click.option("--index", default="https://pypi.org/simple/", help="pypi index url.")
@click.option("-d", "--debug", type=bool, default=False, help="print debugging information")
@click.option("-o", "--out", default="cli", type=str, help="Output format")
def main(index="https://pypi.org/simple/", debug=False, out="cli"):
    ctx["cwd"] = os.getcwd()
    ctx["index"] = index
    ctx["debug"] = debug
    ctx["out"] = out
    ctx["packages"] = {}

    if not check_if_requirements_exists():
        print(
            f"Could not find `requirements.txt` file in current dierctory: {ctx.get('cwd')}."
        )
    else:
        if ctx.get("debug"):
            print(ctx)

        parse_requirements()
        print_formated()


main()
