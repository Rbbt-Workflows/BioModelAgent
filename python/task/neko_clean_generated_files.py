#!/usr/bin/env python3
# Auto-generated wrapper for NeKo clean_generated_files
from neko_task_wrapper import load_server, parse_and_call

if __name__ == '__main__':
    TARGET = 'clean_generated_files'
    mod = load_server()
    func = getattr(mod, TARGET)
    parse_and_call(func)
