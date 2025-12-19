#!/usr/bin/env python3
# Auto-generated wrapper for NeKo check_bnet_files_names
from neko_task_wrapper import load_server, parse_and_call

if __name__ == '__main__':
    TARGET = 'check_bnet_files_names'
    mod = load_server()
    func = getattr(mod, TARGET)
    parse_and_call(func)
