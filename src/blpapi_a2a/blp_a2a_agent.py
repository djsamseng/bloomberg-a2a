
import json
import logging
import typing

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph.graph.graph import CompiledGraph
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.tool import ToolMessage, ToolCall

from mcp import ClientSession

logger = logging.getLogger(__name__)

async def create_ollama_agent(session: ClientSession, ollama_base_url: str, ollama_model: str):
  ollama_chat_llm = ChatOllama(
    base_url=ollama_base_url,
    model=ollama_model,
    temperature=0.2
  )
  tools = await load_mcp_tools(session)
  agent = create_react_agent(ollama_chat_llm, tools=tools)
  return agent

def strip_tool_call_id(t: ToolCall):
  return {
    "name": t.get("name"),
    "args": t.get("args"),
    "type": t.get("type"),
  }

async def run_ollama(
  ollama_agent: CompiledGraph,
  prompt: str
) -> typing.AsyncIterator[str]:
  async for event in ollama_agent.astream(
    input={"messages": prompt},
    stream_mode="updates"
  ):
    if "agent" in event:
      message = event["agent"]["messages"][-1]
      if isinstance(message, AIMessage):
        content = message.content
        tool_calls = message.tool_calls
        if tool_calls is not None:
          tool_calls = [strip_tool_call_id(t) for t in message.tool_calls]
        done = message.response_metadata["done"] if "done" in message.response_metadata else None
        done_reason = done = message.response_metadata["done_reason"] if "done_reason" in message.response_metadata else None
        yield(json.dumps({
          "type": "agent",
          "content": str(content),
          "tool_calls": str(tool_calls),
          "done": done,
          "done_reason": done_reason
        }))
        continue
      logging.error(f"Unknown agent message: {type(message)}")
      continue
    if ("tools" in event):
      message = event["tools"]["messages"][-1]
      if isinstance(message, ToolMessage):
        content = message.content
        name = message.name
        status = message.status
        yield(json.dumps({
          "type": "tools",
          "content": str(content),
          "tool_name": str(name),
          "status": str(status),
        }))
        continue
      logging.error(f"Unknown tools message: {type(message)}")
      continue
    logging.error(f"Unknown ollama event: {type(event)}")
    yield str(event)
