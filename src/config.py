from .const import PIP_DEFAULT_INDEX


CONFIG_OPTIONS = [
    'cwd',
    'index-url',
    'debug',
    'requirements',
    'package',
];


DEFAULT_CONFIG = {
  'index-url': PIP_DEFAULT_INDEX,
  'debug': False,
}


def resolve_config(config_from_file: dict = dict(), **kwargs) -> dict:
    """
    Takes a default configuration, overrides it with local configuration
    from file, such as: `.bsrc`, `bsrc.yaml`, `bsconfig.yaml`
    And overrides this with inputs to the command line,
    results is a dict of configurations.
    """

    overrides = {f'{key}': f'{value}' for key, value in kwargs.items() if key in CONFIG_OPTIONS}

    return {
        **DEFAULT_CONFIG,
        **config_from_file,
        **overrides
    }



