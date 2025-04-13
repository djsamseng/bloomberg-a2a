# Bloomberg A2A

An [A2A](https://github.com/google/A2A) agent providing financial data from Bloomberg blpapi

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
python3 -m bloomberg_a2a
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
