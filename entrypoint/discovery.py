import importlib, os
import toml
from . import main


def is_module_or_package(path, name, ignore):
    if os.path.isdir(os.path.join(path, name)):
        return None if name in ignore else name
    else:
        name, ext = os.path.splitext(name)
        return name if ext == '.py' else None


def _load_everything(qualname, ignore):
    module_or_package = importlib.import_module(qualname)
    if hasattr(module_or_package, '__path__'):
        for path in module_or_package.__path__:
            for name in os.listdir(path):
                fixed_name = is_module_or_package(path, name, ignore)
                if fixed_name is not None:
                    _load_everything(f'{qualname}.{fixed_name}', ignore)


# This only works properly on a fresh run, where nothing has been cached yet.
def _discover_entrypoints(qualname, ignore=('__pycache__',)):
    _load_everything(qualname, ignore)
    return main._REGISTRY


@main.entrypoint(name='entrypoint-update-metadata')
def write_all():
    """Discover entry points in all source files and update pyproject.toml."""
    with open('pyproject.toml') as f:
        data = toml.load(f)
    poetry = data['tool']['poetry']
    poetry['scripts'] = _discover_entrypoints(poetry['name'])
    with open('pyproject.toml', 'w') as f:
        toml.dump(data, f)
