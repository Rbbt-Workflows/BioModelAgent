#!/usr/bin/env python3
"""Wrapper exposing NeKo create_network as a standalone CLI task.

Usage examples:
  python3 neko_create_network.py --list 'TP53' 'MYC' --database omnipath
  python3 neko_create_network.py --scout-metadata
"""
import argparse
import inspect
import importlib.util
import json
import os
import sys
from pathlib import Path

# Path to the NeKo server.py in the repo
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


def _describe_func(func):
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    params = []
    for name, p in sig.parameters.items():
        if name == 'ctx':
            continue
        ann = p.annotation
        default = None if p.default is inspect._empty else p.default
        ptype = 'string'
        try:
            from typing import get_origin, get_args, List
            origin = get_origin(ann)
            if origin is list or origin is List:
                ptype = 'list[string]'
            elif ann is bool:
                ptype = 'boolean'
            elif ann is int:
                ptype = 'integer'
            elif ann is float:
                ptype = 'float'
            else:
                ptype = 'string'
        except Exception:
            ptype = 'string'
        params.append({'name': name, 'type': ptype, 'default': default, 'required': default is None})
    return {'name': func.__name__, 'description': doc.split('\n\n',1)[0] if doc else '', 'params': params}


def main():
    mod = load_server()
    if not hasattr(mod, 'create_network'):
        print('NeKo server module does not expose create_network', file=sys.stderr)
        sys.exit(1)
    func = mod.create_network

    # Support metadata introspection required by workflow helpers
    if '--scout-metadata' in sys.argv:
        meta = _describe_func(func)
        print(json.dumps(meta, ensure_ascii=False))
        return

    parser = argparse.ArgumentParser(description=inspect.getdoc(func).split('\n')[0])
    parser.add_argument('--list', nargs='*', dest='list_of_initial_genes', help='Initial gene list (space separated)')
    parser.add_argument('--database', default='omnipath')
    parser.add_argument('--sif-file', dest='sif_file')
    parser.add_argument('--max-len', dest='max_len', type=int, default=2)
    parser.add_argument('--algorithm', default='bfs')
    parser.add_argument('--only-signed', dest='only_signed', action='store_true')
    parser.add_argument('--no-only-signed', dest='only_signed', action='store_false')
    parser.set_defaults(only_signed=True)
    parser.add_argument('--connect-with-bias', dest='connect_with_bias', action='store_true')
    parser.add_argument('--consensus', dest='consensus', action='store_true')
    parser.add_argument('--session-id', dest='session_id')
    parser.add_argument('--verbosity', default='preview')

    args = parser.parse_args()

    # Prepare call args
    call_kwargs = {
        'list_of_initial_genes': args.list_of_initial_genes or [],
        'ctx': _DummyCtx(),
        'database': args.database,
        'sif_file': args.sif_file,
        'max_len': args.max_len,
        'algorithm': args.algorithm,
        'only_signed': args.only_signed,
        'connect_with_bias': args.connect_with_bias,
        'consensus': args.consensus,
        'session_id': args.session_id,
        'verbosity': args.verbosity,
    }

    res = func(**call_kwargs)
    # If result is complex, print JSON otherwise plain
    if isinstance(res, (dict, list)):
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(res)


if __name__ == '__main__':
    main()
