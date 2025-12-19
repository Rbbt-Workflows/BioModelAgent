#!/usr/bin/env python3
# Auto-generated wrapper for NeKo extend_network
from neko_task_wrapper import load_server, parse_and_call

if __name__ == '__main__':
    TARGET = 'extend_network'
    mod = load_server()
    func = getattr(mod, TARGET)
    parse_and_call(func)
