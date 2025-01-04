"""
Module to manage merging user config with base config

Based on https://github.com/caikit/caikit/blob/main/caikit/config/config.py
"""
# Standard
from enum import Enum

# First Party
import aconfig

_CONFIG_TYPE = dict | aconfig.Config


class ListMergeType(Enum):
    REPLACE = "replace"
    PREPEND = "prepend"
    APPEND = "append"
    INDEX = "index"


def merge_configs(
    base: _CONFIG_TYPE | None,
    overrides: _CONFIG_TYPE | None,
    list_merge_type: ListMergeType = ListMergeType.REPLACE,
) -> aconfig.Config:
    """Helper to perform a deep merge of the overrides into the base. The merge
    is done in place, but the resulting dict is also returned for convenience.
    The merge logic is quite simple: If both the base and overrides have a key
    and the type of the key for both is a dict, recursively merge, otherwise
    set the base value to the override value.
    Args:
        base: The base config that will be updated with the overrides
        overrides: The override config
        list_merge_type: The type of merge logic to use for lists
    Returns:
        merged:
            The merged results of overrides merged onto base
    """
    # Handle none args
    if base is None:
        return overrides or {}
    if overrides is None:
        return base or {}

    # Do the deep merge
    for key, value in overrides.items():
        if (
            key not in base
            or not isinstance(base[key], (dict, list))
            or not isinstance(value, (dict, list))
        ):
            base[key] = value
        elif isinstance(value, list):
            if list_merge_type == ListMergeType.REPLACE:
                base[key] = value
            elif list_merge_type == ListMergeType.PREPEND:
                base[key] = value + base[key]
            elif list_merge_type == ListMergeType.APPEND:
                base[key] = base[key] + value
            elif list_merge_type == ListMergeType.INDEX:
                orig_list = base[key]
                for i, entry in enumerate(value):
                    if i < len(orig_list):
                        orig_list[i] = entry
                    else:
                        orig_list.append(entry)
            else:
                raise ConfigError(f"Bad list merge type: {list_merge_type}")
        else:
            base[key] = merge_configs(base[key], value)

    return base
