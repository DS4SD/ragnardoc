"""
Central configuration for the tool
"""
# Standard
import os

# First Party
import aconfig

# Local
from .merge import merge_configs

BASE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _initialize_config() -> aconfig.ImmutableConfig:
    # Parse the base config with env var overrides
    config = aconfig.Config.from_yaml(BASE_CONFIG_PATH, override_env_vars=True)

    # Make sure '~' is expanded correctly
    config.ragnardoc_home = os.path.expanduser(config.ragnardoc_home)

    # Merge in user overrides
    user_config = os.path.join(config.ragnardoc_home, "config.yaml")
    if os.path.exists(user_config):
        config = merge_configs(config, aconfig.Config.from_yaml(user_config))

    # Return the immutable view
    return aconfig.ImmutableConfig(config)


# Global config object
config_instance = _initialize_config()

# Attribute access
def __getattr__(key: str) -> any:
    return getattr(config_instance, key)
