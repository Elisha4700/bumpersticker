
from typing import Any
from rich.console import Console
from rich.table import Table
# from rich.progress import



def convert_list_to_string(versions):
    out = ""

    for v in versions:
        out += f"{v}" if len(out) == 0 else f", {v}"

    return out

def output_cli(context: dict[str, Any]):
    packages = context.get("packages")

    if not packages:
        return

    table = Table(title="Summary")

    table.add_column("Package Name", justify="right", no_wrap=True)
    table.add_column("Current Version", justify="center", no_wrap=True)
    table.add_column("Available Packages", justify="left", no_wrap=False)

    for package_name, package in packages.items():
        op = package.get("op", "????")
        v = package.get("current_version", "????")
        hv = package.get("higher_versions", [])

        table.add_row(package_name, v, convert_list_to_string(hv))

        # out = Padding(, 20)
        # print(out, op)
        # # print(f"{package_name} {op} {v}         ", hv)
    console = Console()
    console.print(table)


def print_formated(ctx: dict) -> None:
    if ctx.get("out") == "json":
        print(ctx)
        return

    output_cli(context=ctx)


# def print_progress(package_name: str, current_pks_index: int, total_packages: int):
#     task = progress.add_task("[red]Downloading...", total=total_packages)


