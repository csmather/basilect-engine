#!/usr/bin/env python3
"""PreToolUse hook: block writes of invalid JSON to data/artists/"""
import json, sys

data = json.load(sys.stdin)
tool_input = data.get('tool_input', {})
file_path = tool_input.get('file_path', '')

if not file_path.endswith('.json'):
    sys.exit(0)

content = tool_input.get('content', '')
if 'data/artists/' in file_path:
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        print(f"BLOCKED: Invalid JSON in {file_path}\n{e}", file=sys.stderr)
        sys.exit(1)
