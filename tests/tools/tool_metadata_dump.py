import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from tools import tool_map



for tool in list(tool_map.values()):
    print(tool.name)
    print(tool.description)
    print(tool.args_schema.model_json_schema())
