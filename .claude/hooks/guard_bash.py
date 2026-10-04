import json
import re
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

protected = ["expense_tracker.db", "spendly.db", ".env", "migrations"]
destructive = re.compile(
    r"\b(rm|rmdir|del|erase|unlink|truncate|mv|shred|Remove-Item)\b"
    r"|git\s+(clean|rm)\b"
    r"|os\.(remove|unlink)|shutil\.rmtree|DROP\s+TABLE",
    re.IGNORECASE,
)

if destructive.search(cmd):
    for p in protected:
        if p in cmd:
            print(f"BLOCKED: destructive command touches protected path: {p}", file=sys.stderr)
            sys.exit(2)