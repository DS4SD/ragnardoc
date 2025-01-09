"""
Base class for initializers that can be used to auto-initialize ingestion plugin
connections
"""

# Standard
import abc

# Third Party
import yaml

# Local
from ...ingestors.base import Ingestor


class IngestorInitializerBase(abc.ABC):
    __doc__ = __doc__

    @property
    def name(self) -> str:
        return self.ingestor_class().name

    @abc.abstractmethod
    def ingestor_class(self) -> type[Ingestor]:
        """Get the ingestor class for this initializer"""

    @abc.abstractmethod
    def is_installed(self):
        """Determine whether the ingestor is installed"""

    def initialize_config(self) -> dict:
        """Initialize the config for this ingestor"""
        ingestor_class = self.ingestor_class()
        return_dict = {"type": ingestor_class.name}
        config_dict = return_dict.setdefault("config", {})

        # Print out the config schema
        print("CONFIG SCHEMA")
        print(yaml.safe_dump(ingestor_class.config_schema))
        print()
        print("CONFIG_DEFAULTS")
        print(yaml.safe_dump(ingestor_class.config_defaults))
        print()
        # TODO: Figure out required params with no defaults and always ask for
        # them
        while True:
            if input("Enter a config value [Yn]? ").lower() == "n":
                break
            print("HINT: Join nested keys with '.' characters.")
            print("HINT: Lists will always be appended to.")
            key = input("Key: ").strip()
            if not key:
                continue
            val = input("Value: ").strip()
            try:
                self._recursive_set(config_dict, ingestor_class.config_schema, key, val)
            except KeyError as err:
                print(f"Could not set [{key} = {val}]: {err}")
        return return_dict

    @classmethod
    def _recursive_set(cls, config_dict: dict, schema: dict, key: str, val: str):
        """Recursive setter function to add the given key inside the given dict"""
        top_key, _, key_remainder = key.partition(".")
        prop = schema.get("properties", {}).get(top_key, {})
        val_type = prop.get("type")
        if top_key == key:
            if val_type is None:
                raise KeyError(f"Key not in schema: {key}")
            converted = cls._convert_schema_type(val, prop)
            if isinstance(converted, list):
                config_dict.setdefault(key, []).extend(converted)
            else:
                config_dict[key] = converted
        else:
            cls._recursive_set(
                config_dict.setdefault(top_key, {}), prop, key_remainder, val
            )

    @classmethod
    def _convert_schema_type(cls, val: str, prop: dict) -> str | int | float | list:
        val_type = prop.get("type")
        if val_type == "number":
            try:
                return int(val)
            except ValueError:
                return float(val)
        if val_type == "string":
            return val
        if val_type == "array":
            items = prop.get("items", {})
            item_type = items.get("type")
            if item_type in ["object", "array"]:
                raise KeyError(
                    "Cannot set nested objects or arrays here. Use manual config overrides!"
                )
            return [cls._convert_schema_type(val, items)]
        raise ValueError(f"Unsupported type: {val_type}")
