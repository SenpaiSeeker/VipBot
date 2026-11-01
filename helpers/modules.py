import importlib
from functools import wraps
from pathlib import Path

import pyrogram

from .patcher import Object


class Modules(Object):
    registered_modules = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls not in cls.registered_modules:
            cls.registered_modules.append(cls)

    def handle(self, func):
        @wraps(func)
        async def wrapper(client, update):
            try:
                return await func(client, update)
            except (
                pyrogram.errors.MessageNotModified,
                pyrogram.errors.MessageDeleteForbidden,
            ):
                return None
            except Exception as e:
                client.log.print(
                    f"{client.log.RED}[ERROR]: {client.log.CYAN}"
                    f"{func.__module__}.{func.__name__} "
                    f"{client.log.WHITE}| {client.log.YELLOW}{type(e).__name__}: "
                    f"{client.log.RED}{e}"
                )

        return wrapper

    def load_all(self, directory="VvipBot"):
        target_dir = Path(directory)
        if not target_dir.exists():
            return self

        for py_path in sorted(target_dir.rglob("*.py")):
            if py_path.name.startswith("__"):
                continue

            rel_parts = py_path.relative_to(target_dir.parent).with_suffix("").parts
            module_name = ".".join(rel_parts)
            importlib.import_module(module_name)

        if not hasattr(self.client, "_active_module_instances"):
            self.client._active_module_instances = []

        for module_class in self.registered_modules:
            already_active = any(
                isinstance(instance, module_class)
                for instance in self.client._active_module_instances
            )
            if not already_active:
                instance = module_class(self.client)
                self.client._active_module_instances.append(instance)

        return self


def _client_load_all(self, directory="VvipBot"):
    return self.ns.modules.load_all(directory)


setattr(pyrogram.client.Client, "load_all", _client_load_all)
