
import logging

from typing import AsyncIterable

from mcp import ClientSession, StdioServerParameters
from mcp import types as mcp_types
from mcp.client.stdio import stdio_client

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent


from google_a2a.common.server.task_manager import InMemoryTaskManager
from google_a2a.common.types import JSONRPCResponse, SendTaskRequest, SendTaskResponse, SendTaskStreamingRequest, SendTaskStreamingResponse

logger = logging.getLogger(__name__)

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


class BlpA2ATaskManager(InMemoryTaskManager):
  def __init__(
    self
  ):
    super().__init__()

  async def setup_tools(self, ollama_base_url: str, ollama_model: str):
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

        if ollama_base_url is not None and ollama_model is not None:

          await run_ollama(session=session, ollama_base_url=ollama_base_url, ollama_model=ollama_model)

        else:
          resources = await session.list_resources()
          print("Available resources:", resources)

          tools = await session.list_tools()
          print("Available tools:", tools)


  async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
    return await super().on_send_task(request)

  async def on_send_task_subscribe(self, request: SendTaskStreamingRequest) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
    return await super().on_send_task_subscribe(request)
