

import argparse
import asyncio
import typing

from mcp import ClientSession, StdioServerParameters
from mcp import types as mcp_types
from mcp.client.stdio import stdio_client

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from bloomberg_a2a.blp_a2a_task_manager import BlpA2ATaskManager

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--ollama-host", type=str, help="Host address for ollama. Ex: http://127.0.0.1:11434")
  parser.add_argument("--ollama-model", type=str, default=None, help="The ollama model being used. Ex: gemma3:27b")
  return parser.parse_args()

async def run_ollama(session: ClientSession, ollama_base_url: str, ollama_model: str):
  print("Using ollama:", ollama_base_url, ollama_model)
  ollama_chat_llm = ChatOllama(
    base_url=ollama_base_url,
    model=ollama_model,
    temperature=0.2
  )
  tools = await load_mcp_tools(session)
  # TODO: Create a tool to query relevant tickers
  # TODO: Create a tool to query relevant fields
  # TODO: System prompt to have the agent retrieve tickers and fields for the request
  agent = create_react_agent(ollama_chat_llm, tools)

  prompt = "What is today's price for AAPL US Equity?"
  agent_response = await agent.ainvoke(
    {"messages": prompt }
  )
  print("Prompt:", prompt)
  print("Response:", agent_response["messages"])

async def run():
  args = parse_args()

  server_params = StdioServerParameters(
    command="uv",
    args=["run", "bloomberg-mcp"],
    env=None,
  )

  async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(
      read_stream=read_stream,
      write_stream=write_stream,
    ) as session:
      await session.initialize()

      if args.ollama_host is not None and args.ollama_model is not None:
        ollama_base_url = args.ollama_host
        ollama_model = args.ollama_model

        await run_ollama(session=session, ollama_base_url=ollama_base_url, ollama_model=ollama_model)

      else:
        resources = await session.list_resources()
        print("Available resources:", resources)

        tools = await session.list_tools()
        print("Available tools:", tools)


def main() -> None:
  asyncio.run(run())


if __name__ == "__main__":
  main()
