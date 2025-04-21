# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "asyncio",
#     "blpapi-mcp",
#     "langchain",
#     "langchain-mcp-adapters",
#     "langchain-ollama",
#     "langgraph",
#     "mcp[cli]",
# ]
#
# [tool.uv.sources]
# blpapi-mcp = { git = "https://github.com/djsamseng/blpapi-mcp" }
# ///

import asyncio
import logging
import json
import httpx
import platform
import typing
import langgraph.config
import langgraph.graph.message
import typing_extensions

from langchain_ollama import ChatOllama
from langchain_mcp_adapters.tools import load_mcp_tools, BaseTool
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.graph.graph import CompiledGraph
from langgraph.graph import StateGraph
from langgraph.store.base import BaseStore
import langgraph.graph

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.tool import ToolMessage, ToolCall

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_name = "qwq"

class State(typing_extensions.TypedDict):
  messages: typing.Annotated[list, langgraph.graph.message.add_messages]

async def tool_node_afunc(
  message: AIMessage,
  tools_by_name: typing.Dict[str, BaseTool],
):
  outputs = []
  for tool_call in message.tool_calls:
    tool = tools_by_name[tool_call["name"]]
    args = tool_call["args"]
    logger.info(f"Invoking tool: {tool.name} with args {args}")
    try:
      result = await tool.ainvoke(args)
      logger.info(f"Tool result: {result}")
      outputs.append(
        ToolMessage(
          content=json.dumps(result),
          name=tool.name,
          tool_call_id=tool_call["id"]
        )
      )
    except Exception as e:
      error_message = f"Failed to invoke tool {tool.name}. Reason: {e}"
      logger.error(error_message)
      outputs.append(
        ToolMessage(
          content=error_message,
          name=tool.name,
          tool_call_id=tool_call["id"]
        )
      )
  return {
    "messages": outputs,
  }



def graph_router(
  state: State,
):
  if messages := state.get("messages", []):
    ai_message = messages[-1]
    if len(messages) >= 4:
      return langgraph.graph.END
  else:
    raise ValueError("No messages for graph_router")
  if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
    return "tools"
  return langgraph.graph.END

async def run_ollama_custom_graph(session: ClientSession):
  graph_builder = StateGraph(State)
  llm = ChatOllama(
      model=model_name,
      base_url="http://127.0.0.1:11434",
      extract_reasoning=True,
  )
  tools = await load_mcp_tools(session=session)
  llm_with_tools = llm.bind_tools(tools=tools)

  def chatbot(state: State):
    messages = state["messages"]

    logging.info(f"Invoking LLM: {messages}")

    result = llm_with_tools.invoke(messages)
    # qwq is trained to output no content only tool_calls
    # when tools is present in the POST request json
    logging.info(f"LLM result: {result}")
    return {
      "messages": [result]
    }
  tools_by_name = {tool.name: tool for tool in tools}
  async def tool_node(state: State):
    if messages := state.get("messages", []):
      message = messages[-1]
    else:
      raise ValueError("No input messages")
    return await tool_node_afunc(
      message=message,
      tools_by_name=tools_by_name
    )

  graph_builder.add_node("chatbot", chatbot)
  graph_builder.add_edge(langgraph.graph.START, "chatbot")
  graph_builder.add_node("tools", tool_node)
  # Conditionally go from chatbot to elsewhere
  graph_builder.add_conditional_edges(
    "chatbot",
    graph_router,
    {
      "tools": "tools",
      langgraph.graph.END: langgraph.graph.END,
    },
  )
  graph_builder.add_edge("tools", "chatbot")

  graph = graph_builder.compile()
  await run_graph(graph=graph)

async def run_graph(graph: CompiledGraph):
  inputs = {
    "messages": [
      ("user", "What is the price of apple? Explain your thinking at every step")
    ]
  }
  async for s in graph.astream(inputs, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
      print(message)
    else:
      message.pretty_print()


async def run_ollama(session: ClientSession):
  llm = ChatOllama(
      model=model_name,
      base_url="http://127.0.0.1:11434"
  )
  tools = await load_mcp_tools(session=session)
  graph = create_react_agent(model=llm, tools=tools)
  await run_graph(graph=graph)



async def run_custom_tools(session: ClientSession):
  client = httpx.Client(
    base_url="http://127.0.0.1:11434",
    timeout=None,
    headers={
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': f'ollama-python/{"0.0.0"} ({platform.machine()} {platform.system().lower()}) Python/{platform.python_version()}',
    }
  )
  model_name = "gemma3:27b"
  prompt1 = """What is the price of companies related to APPL?

When you need to use a tool, format your response as JSON as follows:
<tool>
{"name": "tool_name", "parameters": {"param1": "value1", "param2": "value2"}}
</tool>

Always include your thinking as follows:
<think>
My reasoning is...
</think>

Only output an answer when you have a final answer for the user. There should be no tool_call if there is an answer
<answer>
The answer is ...
</answer>

You have the available tools
{"name": "bdh", "description": "Get Bloomberg historical data", "parameters": {"tickers": ["ticker_name"], "flds": ["Bloomberg_ticker_field_name"]}, "returns": ["field_value_1", "field_value_2", ...]}
{"name": "rv", "description": "Get related tickers to the one provided", "parameters": {"ticker": "ticker_name"}, "returns": ["related_ticker_1", "related_ticker_2", ...]}

Your output should only contain
<think>
</think>
<tool>
</tool>
<answer>
</answer>

Here are your previous thoughts and the results of any tool calls.

<history> should not be included in your response.
<tool_call> should not be included in your response.

"""
  prompt2 = prompt1 + """
<history>
<1>
<think>
The user asks for the price of companies related to APPL. First, I need to find the related companies to APPL using the 'rv' tool. Then I will use the 'bdh' tool to retrieve the last price for each related company.
</think>
<tool>
{"name": "rv", "parameters": {"ticker": "APPL"}}
</tool>
<tool_call>
{"returns": ["IBM US Equity", "GOOG US Equity", "MSFT US Equity"]}
</tool_call>
</1>
</history>
"""
  prompt3 = prompt1 + """
<history>
<1>
<think>
The user asks for the price of companies related to APPL. First, I need to find the related companies to APPL using the 'rv' tool. Then I will use the 'bdh' tool to retrieve the last price for each related company.
</think>
<tool>
{"name": "rv", "parameters": {"ticker": "APPL"}}
</tool>
<tool_call>
{"returns": ["IBM US Equity", "GOOG US Equity", "MSFT US Equity"]}
</tool_call>
</1>
<2>
<think>
Now that I have the related tickers (IBM, GOOG, MSFT), I will use the 'bdh' tool to get the last price for each of them.
</think>
<tool>
{"name": "bdh", "parameters": {"tickers": ["IBM US Equity", "GOOG US Equity", "MSFT US Equity"], "flds": ["PX_LAST"]}}
</tool>
<tool_call>
{"returns": ["123.12", "244.02", "315.92"]}
</2>
</history>

"""


  def send_request_for_prompt(prompt):
    request = {
      "model": model_name,
      "stream": True,
      "options": {},
      "messages": [{
        "role": "user",
        "content": prompt
      }],
      "tools": []
    }
    with client.stream("POST", "/api/chat", json=request) as r:
      print("Receiving response...")
      all_lines = []
      for line in r.iter_lines():
        try:
          content = json.loads(line)
          all_lines.append(content["message"]["content"])
        except Exception as e:
          all_lines.append(line)
      print("".join(all_lines))
  print("======== PROMPT 1 ========")
  send_request_for_prompt(prompt1)
  print("======== PROMPT 2 ========")
  send_request_for_prompt(prompt2)
  print("======== PROMPT 3 ========")
  send_request_for_prompt(prompt3)



async def run_client():
  server_params = StdioServerParameters(
    command="uv",
    args=["run", "blpapi-mcp"],
    env=None,
  )
  async with stdio_client(server=server_params) as (read_stream, write_stream):
    async with ClientSession(
      read_stream=read_stream,
      write_stream=write_stream,
    ) as session:
      await session.initialize()

      #await run_ollama(session)
      #await run_ollama_custom_graph(session)
      await run_custom_tools(session)

def main() -> None:
  asyncio.run(run_client())


if __name__ == "__main__":
    main()
