from tools import tool_map



for tool in list(tool_map.values()):
    print(tool.name)
    print(tool.description)
    print(tool.args_schema.model_json_schema())
