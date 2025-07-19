
run-local:
    @mcphost -m ollama:qwen3 --config mcp_config.json

run-openai:
    @mcphost -m openai:gpt-4 --config mcp_config.json 
