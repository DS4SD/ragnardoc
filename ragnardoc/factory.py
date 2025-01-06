"""
This toolkit utility provides common factory construction semantics and a common
base class for classes that can be constructed via config

Derived from: https://github.com/caikit/caikit/blob/main/caikit/core/toolkit/factory.py
"""

# Standard
import abc
import importlib

# First Party
import aconfig
import alog

log = alog.use_channel("FCTRY")


class FactoryConstructible(abc.ABC):
    """A class can be constructed by a factory if its constructor takes exactly
    one argument that is an aconfig.Config object and it has a name to identify
    itself with the factory.
    """

    @property
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        """This is the name of this constructible type that will be used by
        the factory to identify this class
        """

    @abc.abstractmethod
    def __init__(self, config: aconfig.Config, instance_name: str, **kwargs):
        """A FactoryConstructible object must be constructed with a config
        object that it uses to pull in all configuration
        """


class Factory:
    """The base factory class implements all common factory functionality to
    read a designated portion of config and instantiate an instance of the
    registered classes.
    """

    # The keys in the instance config
    TYPE_KEY = "type"
    CONFIG_KEY = "config"

    def __init__(self, name: str):
        """Construct with the path in the global config where this factory's
        configuration lives.
        """
        self._name = name
        self._registered_types = {}

    @property
    def name(self) -> str:
        return self._name

    def register(self, constructible: type[FactoryConstructible]):
        """Register the given constructible"""
        current = self._registered_types.get(constructible.name)
        assert (
            current is None or current is constructible
        ), f"Conflicting registration of {constructible.name}"
        self._registered_types[constructible.name] = constructible

    def construct(
        self,
        instance_config: dict,
        instance_name: str | None = None,
        **kwargs,
    ) -> FactoryConstructible:
        """Construct an instance of the given type"""
        inst_type = instance_config.get(self.__class__.TYPE_KEY)
        inst_cfg = aconfig.Config(
            instance_config.get(self.__class__.CONFIG_KEY, {}),
            override_env_vars=False,
        )
        inst_cls = self._registered_types.get(inst_type)
        assert (
            inst_cls is not None
        ), f"No {self.name} class registered for type {inst_type}"
        instance_name = instance_name or inst_cls.name
        return inst_cls(inst_cfg, instance_name, **kwargs)


class ImportableFactory(Factory):
    """An ImportableFactory extends the base Factory to allow the construction
    to specify an "import_class" field that will be used to import and register
    the implementation class before attempting to initialize it.
    """

    IMPORT_CLASS_KEY = "import_class"

    def construct(
        self,
        instance_config: dict,
        instance_name: str | None = None,
        **kwargs,
    ):
        # Look for an import_class and import and register it if found
        import_class_val = instance_config.get(self.__class__.IMPORT_CLASS_KEY)
        if import_class_val:
            assert isinstance(str, import_class_val)
            module_name, class_name = import_class_val.rsplit(".", 1)
            imported_module = importlib.import_module(module_name)
            imported_class = getattr(imported_module, class_name)
            assert issubclass(imported_class, FactoryConstructible)

            self.register(imported_class)
        return super().construct(instance_config, instance_name, **kwargs)
