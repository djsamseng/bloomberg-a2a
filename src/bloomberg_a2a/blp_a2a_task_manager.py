
import logging

import typing
from typing import AsyncIterable

from mcp import ClientSession, StdioServerParameters
from mcp import types as mcp_types
from mcp.client.stdio import stdio_client

from langgraph.graph.graph import CompiledGraph


from google_a2a.common.server.task_manager import InMemoryTaskManager
from google_a2a.common.types import (
  Artifact,
  JSONRPCError,
  JSONRPCResponse,
  Message,
  Part,
  SendTaskRequest,
  SendTaskResponse,
  SendTaskStreamingRequest,
  SendTaskStreamingResponse,
  Task,
  TaskState,
  TaskStatus,
  TextPart,
)

from bloomberg_a2a.blp_a2a_agent import create_ollama_agent, run_ollama

logger = logging.getLogger(__name__)

class BlpA2ATaskManager(InMemoryTaskManager):
  INPUT_MODES = ["text", "text/plain"]
  OUTPUT_MODES = ["text", "text/plain"]

  def __init__(
    self
  ):
    super().__init__()
    self.ollama_agent: typing.Union[None, CompiledGraph] = None

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
          self.ollama_agent = await create_ollama_agent(
            session=session,
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
          )
        else:
          resources = await session.list_resources()
          print("Available resources:", resources)

          tools = await session.list_tools()
          print("Available tools:", tools)


  async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
    try:
      await self.upsert_task(request.params)
      task_id = request.params.id
      received_text = typing.cast(TextPart, request.params.message.parts[0]).text
      response_text = f"No AI agent running to process the request"
      if self.ollama_agent is not None:
        response_text = await run_ollama(ollama_agent=self.ollama_agent, prompt=received_text)
      task = await self._update_task(
        task_id=task_id,
        task_state=TaskState.COMPLETED,
        response_text=response_text
      )
      return SendTaskResponse(id=request.id, result=task)
    except Exception as e:
      return SendTaskResponse(
        id=request.id,
        error=JSONRPCError(
          code=-32000, # Server error
          message=f"Server error: {str(e)}"
        )
      )

  async def on_send_task_subscribe(self, request: SendTaskStreamingRequest) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
    # Not implemented as AgentCapabilities set to streaming=False
    return await super().on_send_task_subscribe(request)

  async def _update_task(
    self,
    task_id: str,
    task_state: TaskState,
    response_text: str,
  ) -> Task:
    task = self.tasks[task_id]
    agent_response_parts = [
      typing.cast(Part, {
        "type": "text",
        "text": response_text,
      })
    ]
    task.status = TaskStatus(
      state=task_state,
      message=Message(
        role="agent",
        parts=agent_response_parts,
      )
    )
    task.artifacts = [
      Artifact(
        parts=agent_response_parts,
      )
    ]
    return task
