

import argparse

from blpapi_a2a.blp_a2a_server import run_server

def parse_args():
  parser = argparse.ArgumentParser()

  parser.add_argument("--host", type=str, help="Address to run the server on. Ex: 127.0.0.1", default="127.0.0.1")
  parser.add_argument("--port", type=int, help="Port to run the server on. Ex: 8000", default=8000)

  parser.add_argument("--ollama-host", type=str, help="Host address for ollama. Ex: http://127.0.0.1:11434")
  parser.add_argument("--ollama-model", type=str, default=None, help="The ollama model being used. Ex: gemma3:27b")

  return parser.parse_args()



def main() -> None:
  args = parse_args()
  run_server(args)


if __name__ == "__main__":
  main()
