
import asyncio
import logging

import typing
from typing import AsyncIterable

from mcp import ClientSession, StdioServerParameters
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
  TaskStatusUpdateEvent,
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
          logging.info("Available resources:", resources)

          tools = await session.list_tools()
          logging.info("Available tools:", tools)


  async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
    try:
      await self.upsert_task(request.params)
      task_id = request.params.id
      received_text = typing.cast(TextPart, request.params.message.parts[0]).text
      response_text = f"No AI agent running to process the request"
      if self.ollama_agent is not None:
        async for part in run_ollama(ollama_agent=self.ollama_agent, prompt=received_text):
          # Overwrite, thus only sending the last
          response_text = part
      task = await self._update_task(
        task_id=task_id,
        task_state=TaskState.COMPLETED,
        response_text=response_text
      )
      return SendTaskResponse(id=request.id, result=task)
    except Exception as e:
      logger.error(f"Failed to process on_send_task: {str(e)}")
      return SendTaskResponse(
        id=request.id,
        error=JSONRPCError(
          code=-32000, # Server error
          message=f"Server error: {str(e)}"
        )
      )

  async def on_send_task_subscribe(self, request: SendTaskStreamingRequest) -> typing.Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
    try:
      await self.upsert_task(request.params)
      task_id = request.params.id
      sse_event_queue = await self.setup_sse_consumer(task_id=task_id)
      asyncio.create_task(self._stream_ollama_responses(request))
      # This is actually the correct return signature and should not be awaited
      return self.dequeue_events_for_sse(
        request_id=request.id,
        task_id=task_id,
        sse_event_queue=sse_event_queue
      ) # type: ignore
    except Exception as e:
      logger.error(f"Failed to process on_send_task_subscribe: {str(e)}")
      return JSONRPCResponse(
        id=request.id,
        error=JSONRPCError(
          code=-32000,
          message=f"Server error: {str(e)}"
        )
      )

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

  async def _stream_ollama_responses(self, request: SendTaskStreamingRequest):
    task_id = request.params.id
    if self.ollama_agent is None:
      task_status = TaskStatus(
        state=TaskState.CANCELED,
        message=Message(
          role="agent",
          parts=[
            typing.cast(Part, {
              "type": "text",
              "text": "No ollama agent running to process the request"
            })
          ]
        )
      )
      task_update_event = TaskStatusUpdateEvent(
        id=task_id,
        status=task_status,
        final=True,
      )
      await self.enqueue_events_for_sse(
        task_id=task_id,
        task_update_event=task_update_event,
      )
      return

    try:
      received_text = typing.cast(TextPart, request.params.message.parts[0]).text
      async for part in run_ollama(ollama_agent=self.ollama_agent, prompt=received_text):
        # Send each iteration of what the AI model is thinking
        response_text = part
        task_status = TaskStatus(
          state=TaskState.WORKING,
          message=Message(
            role="agent",
            parts=[
              typing.cast(Part, {
                "type": "text",
                "text": response_text,
              })
            ]
          )
        )
        task_update_event = TaskStatusUpdateEvent(
          id=task_id,
          status=task_status,
          final=False,
        )
        await self.enqueue_events_for_sse(
          task_id=task_id,
          task_update_event=task_update_event,
        )

      task_status = TaskStatus(
        state=TaskState.COMPLETED,
        message=None
      )
      task_update_event = TaskStatusUpdateEvent(
        id=task_id,
        status=task_status,
        final=True,
      )
      await self.enqueue_events_for_sse(
        task_id=task_id,
        task_update_event=task_update_event,
      )
    except Exception as e:
      logging.error(f"Failed in _stream_ollama_responses: {str(e)}")
      task_status = TaskStatus(
        state=TaskState.FAILED,
        message=Message(
          role="agent",
          parts=[
            typing.cast(Part, {
              "type": "text",
              "text": f"An error occurred streaming responses: {str(e)}"
            })
          ]
        )
      )
      task_update_event = TaskStatusUpdateEvent(
        id=task_id,
        status=task_status,
        final=True,
      )
      await self.enqueue_events_for_sse(
        task_id=task_id,
        task_update_event=task_update_event,
      )
