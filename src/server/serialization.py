from typing import Any

from cattrs.preconf.json import make_converter

converter = make_converter()


def unstructure(value: object) -> Any:
    return converter.unstructure(value)
