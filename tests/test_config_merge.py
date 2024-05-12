import pytest

from src.config import resolve_config



@pytest.mark.parametrize('config_file, overrides, result', [
    (
        None,
        None,
        {
            'index-url': 'https://pypi.org/simple/',
            'debug': True,
        },
    )
])
def test_my_config_merge(config_file, overrides, result):
    if overrides is None:
        overrides = {}

    assert resolve_config(config_from_file=config_file, **overrides) == result


