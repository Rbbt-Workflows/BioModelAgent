#!/usr/bin/env python3
"""Generic NeKo task wrapper. This file should be copied/instantiated per-tool with TARGET set.
"""
import argparse
import inspect
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import get_origin, get_args

HERE = Path(__file__).resolve().parent
NEKO_PATH = (HERE / '..' / '..' / 'mcp-biomodelling-servers' / 'NeKo' / 'server.py').resolve()


def load_server():
    spec = importlib.util.spec_from_file_location("neko_server", str(NEKO_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _DummyCtx:
    def info(self, *a, **k):
        print("[neko.info]", *a, file=sys.stderr)

    def warning(self, *a, **k):
        print("[neko.warn]", *a, file=sys.stderr)

    def error(self, *a, **k):
        print("[neko.err]", *a, file=sys.stderr)


def parse_and_call(func):
    sig = inspect.signature(func)
    parser = argparse.ArgumentParser(description=(inspect.getdoc(func) or '').split('\n')[0])
    # Add metadata flag
    parser.add_argument('--scout-metadata', action='store_true', help='Print function metadata as JSON and exit')

    arg_names = []
    for name, p in sig.parameters.items():
        if name == 'ctx':
            continue
        ann = p.annotation
        default = None if p.default is inspect._empty else p.default
        arg_names.append(name)
        # Determine type
        origin = get_origin(ann)
        if origin in (list, list.__class__):
            # List types: accept multiple values
            parser.add_argument(f'--{name}', nargs='*', default=default)
        elif ann is bool:
            # Boolean flags
            if default is True:
                parser.add_argument(f'--no-{name}', dest=name, action='store_false')
                parser.add_argument(f'--{name}', dest=name, action='store_true')
                parser.set_defaults(**{name: default})
            else:
                parser.add_argument(f'--{name}', dest=name, action='store_true')
                parser.set_defaults(**{name: default})
        elif ann is int:
            parser.add_argument(f'--{name}', type=int, default=default)
        elif ann is float:
            parser.add_argument(f'--{name}', type=float, default=default)
        else:
            parser.add_argument(f'--{name}', default=default)

    parsed, unknown = parser.parse_known_args()
    if getattr(parsed, 'scout_metadata', False):
        # build metadata
        params = []
        for name, p in sig.parameters.items():
            if name == 'ctx':
                continue
            ann = p.annotation
            default = None if p.default is inspect._empty else p.default
            ptype = 'string'
            origin = get_origin(ann)
            if origin is list:
                ptype = 'list[string]'
            elif ann is bool:
                ptype = 'boolean'
            elif ann is int:
                ptype = 'integer'
            elif ann is float:
                ptype = 'float'
            params.append({'name': name, 'type': ptype, 'default': default, 'required': default is None})
        meta = {'name': func.__name__, 'description': (inspect.getdoc(func) or '').split('\n\n',1)[0], 'params': params}
        print(json.dumps(meta, ensure_ascii=False))
        return

    # Build kwargs
    kwargs = {}
    for name, p in sig.parameters.items():
        if name == 'ctx':
            kwargs['ctx'] = _DummyCtx()
            continue
        val = getattr(parsed, name, None)
        # If a list param and val is None, set to []
        ann = p.annotation
        origin = get_origin(ann)
        if origin is list and val is None:
            val = []
        kwargs[name] = val

    res = func(**kwargs)
    if isinstance(res, (dict, list)):
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(res)


if __name__ == '__main__':
    # Replace TARGET below in generated scripts
    TARGET = '__TARGET__'
    mod = load_server()
    if not hasattr(mod, TARGET):
        print(f'Function {TARGET} not found in NeKo server', file=sys.stderr)
        sys.exit(1)
    func = getattr(mod, TARGET)
    parse_and_call(func)
