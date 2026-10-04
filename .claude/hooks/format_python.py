import json
import subprocess
import sys

data = json.load(sys.stdin)
path = data.get("tool_input", {}).get("file_path", "")
if path.endswith(".py"):
    subprocess.run([sys.executable, "-m", "black", "--quiet", path], check=False)