import re

from typing import List
from pathlib import Path


def is_prebuit(file_name: str):
    file_extension = Path(file_name).suffix
    return file_extension == ".whl" or file_extension == ".egg"


def remove_duplicates(versions) -> List[str]:
    vers = set(versions)
    return [v for v in vers]


def extract_version(v: str):
    result = re.match("^(\d+).(\d+).(\d+).(\d+)", v)

    if not result:
        result = re.match("^(\d+).(\d+).(\d+)", v)

    if not result:
        result = re.match("^(\d+).(\d+)", v)

    if result:
        return ".".join(list(result.groups()))

    return None


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
        .replace(".win32", "")
        .replace(".win", "")
        .replace(".zip", "")
        .replace(".macosx", "")
    )
    return extract_version(v=v)
