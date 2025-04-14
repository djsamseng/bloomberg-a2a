# Bloomberg A2A

An [A2A](https://github.com/google/A2A) agent providing financial data from Bloomberg blpapi.

Leverages [Bloomberg-MCP](https://github.com/djsamseng/bloomberg-mcp) as the data provider.

## Installation
### Using [UV](https://docs.astral.sh/uv/getting-started/installation/)
- First add an index to bloomberg blpapi in `pyproject.toml`
```
[[tool.uv.index]]
name = "blpapi"
url = "https://blpapi.bloomberg.com/repository/releases/python/simple/"
```

```bash
uv add git+https://github.com/djsamseng/bloomberg-a2a
```

## Run the A2A Agent
```bash
uv run bloomberg-a2a
```

## Examples
### Run with ollama
- First [install ollama](https://ollama.com/download)
- Run the ollama server
  - note you may have to `systemctl stop ollama` if you run into [Error: listen tcp 127.0.0.1:11434: bind: address already in use](https://github.com/ollama/ollama/issues/707#issuecomment-1752096265)
```bash
OLLAMA_CONTEXT_LENGTH=8192 ollama serve
```
- Pull down the model `llama3.2:1b`
  - or replace with a model that fits on your GPU that has the `tools` tag
  - Consider `qwq` for an RTX 3090 24GB GPU
```bash
ollama pull llama3.2:1b
```
- Run the agent. Replace host and port with the value of OLLAMA_HOST printed from running `ollama serve` from above
```bash
uv run bloomberg-a2a --ollama-host http://127.0.0.1:11434 --ollama-model llama3.2:1b
```



## Development
### Requirements
1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
2. Clone this repository
```bash
git clone https://github.com/djsamseng/bloomberg-a2a
```
3. Setup the venv
```bash
uv venv
source .venv/bin/activate
```
4. Run the A2A agent
```bash
uv run bloomberg-a2a
```
