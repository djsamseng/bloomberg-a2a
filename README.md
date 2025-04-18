# Bloomberg A2A

An [A2A](https://github.com/google/A2A) agent providing financial data from Bloomberg blpapi.

Leverages [Bloomberg-MCP](https://github.com/djsamseng/bloomberg-mcp) as the data provider.

## Installation
### Using [UV](https://docs.astral.sh/uv/getting-started/installation/)

```bash
uv add git+https://github.com/djsamseng/bloomberg-a2a
```

## Run the A2A Agent without a model
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
```bash
uv run bloomberg-a2a --ollama-host http://127.0.0.1:11434 --ollama-model qwq
```
- Run the test client to interact with the A2A server
```bash
uv run google-a2a-cli --agent http://127.0.0.1:8000
```
- With `qwq` as the LLM you will see the agent call bloomberg-mcp bdp correctly
```
=========  starting a new task ========

What do you want to send to the agent? (:q or quit to exit): What is the price of IBM?

{"role":"agent","parts":[{"type":"text","text":"<think>\nOkay, the user asked for the price of IBM, and I tried using the bdp function. But there was an error: ClosedResourceError() ... typically indicates a disconnected Bloomberg session or invalid API context. Please ensure:\n\n1. Bloomberg Terminal/desktop is running\n2. Python/blpapi session is active\n3. Proper Bloomberg API authentication"}]}
```
- Note: The test client may time out while the ollama server loads a large model. Rerun the test client after the ollama server finishes loading the model weights into memory.



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
