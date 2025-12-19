#!/usr/bin/env python3
# Auto-generated wrapper for NeKo create_session
load_server, parse_and_call
from neko_task_wrapper import load_server, parse_and_call load_server, parse_and_call

if __name__ == '__main__':
    TARGET = 'create_session'
    mod = load_server()
    func = getattr(mod, TARGET)
    parse_and_call(func)
