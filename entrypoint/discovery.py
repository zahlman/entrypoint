import importlib, os


def _module_entrypoints(qualname, module):
    with open(module.__file__) as f:
        deffed = [
            line[4:].partition('(')[0] for line in f if line.startswith('def')
        ]
    for symbol in deffed:
        thing = getattr(module, symbol)
        assert callable(thing)
        try:
            # Ensure all three attributes are present, but only use the name.
            entrypoint_name, _, _ = (
                thing.entrypoint_name, thing.entrypoint_desc, thing.invoke
            )
            yield (entrypoint_name, f'{qualname}:{symbol}.invoke')
        except AttributeError:
            continue


def is_module_or_package(path, name, ignore):
    if os.path.isdir(os.path.join(path, name)):
        return None if name in ignore else name
    else:
        name, ext = os.path.splitext(name)
        return name if ext == '.py' else None


def discover_entrypoints(qualname, ignore=('__pycache__',)):
    module_or_package = importlib.import_module(qualname)
    if not hasattr(module_or_package, '__path__'):
        yield from _module_entrypoints(qualname, module_or_package)
        return
    for path in module_or_package.__path__:
        for name in os.listdir(path):
            fixed_name = is_module_or_package(path, name, ignore)
            if fixed_name is not None:
                yield from discover_entrypoints(f'{qualname}.{fixed_name}')
