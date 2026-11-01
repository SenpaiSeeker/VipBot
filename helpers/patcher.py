import json

import pyrogram


class NamespaceProxy:
    def __init__(self, client):
        self._client = client
        self._instances = {}

    def _register(self, name, instance):
        self._instances[name] = instance

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        if name in self._instances:
            return self._instances[name]

        if name == "telegram":
            return DataObject(arg=self.arg, button=self.buttons)

        if name == "utils":
            return DataObject(
                log=self.log,
                faker=self.faker,
                grad=self.grad,
                dashboard=self.dashboard,
            )

        if name == "server":
            return DataObject(monitor=self.monitor)

        factory = getattr(type(self), f"_factory_{name}", None)
        if factory:
            instance = factory(self._client)
            self._instances[name] = instance
            return instance

        raise AttributeError(f"Helper '{name}' tidak terdaftar pada namespace.")


class Object:
    def __init__(self, client, *args, **kwargs):
        self.client = client
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        aliases = getattr(cls, "_ns_aliases", None)
        if aliases is None:
            alias = getattr(cls, "_ns_alias", cls.__name__.lower())
            aliases = (alias,)

        def factory_method(client_instance):
            return cls(client_instance)

        for alias in aliases:
            setattr(NamespaceProxy, f"_factory_{alias}", staticmethod(factory_method))

            def get_client_property(self, _alias=alias):
                return getattr(self.ns, _alias)

            setattr(pyrogram.client.Client, alias, property(get_client_property))


class DataObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        def _serialize(obj):
            if isinstance(obj, (list, tuple)):
                return [_serialize(item) for item in obj]
            if isinstance(obj, dict):
                return {key: _serialize(value) for key, value in obj.items()}
            if isinstance(obj, DataObject):
                result = {"_": obj.__class__.__name__}
                for key, value in obj.__dict__.items():
                    if key.startswith("_"):
                        continue
                    result[key] = _serialize(value)
                return result
            return obj

        return _serialize(self)

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4, ensure_ascii=False)

    def __repr__(self):
        return self.__str__()


def get_clean_namespace(self):
    if not hasattr(self, "_active_namespace_proxy"):
        setattr(self, "_active_namespace_proxy", NamespaceProxy(self))
    return getattr(self, "_active_namespace_proxy")


setattr(pyrogram.client.Client, "ns", property(get_clean_namespace))
