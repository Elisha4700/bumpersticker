import os
import toml

from typing import Optional


CONFIG_FILE_NAMES = [
    ".bsrc",
    ".bsconfrc",
    "bsconf.toml",
]


def parse_config_from_file(conf_file: str) -> Optional[dict]:
    with open(conf_file) as f:
        config = toml.loads(f.read())
        print('Config', config)
        return config



def get_config_from_file(ctx: dict) -> Optional[dict]:
    for conf_name in CONFIG_FILE_NAMES:
        print(f"Ckecking for config file: {conf_name}")
        if os.path.exists(f"{ctx.get('cwd')}/{conf_name}"):
            if ctx.get("debug"):
                print(f"Conf file: {conf_name}")
                return parse_config_from_file(conf_file=f"{ctx.get('cwd')}/{conf_name}")

