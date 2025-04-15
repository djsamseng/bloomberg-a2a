
import argparse
import logging

from google_a2a.common.server import A2AServer
from google_a2a.common.types import AgentCard, AgentCapabilities, AgentSkill

from bloomberg_a2a.blp_a2a_task_manager import BlpA2ATaskManager

logger = logging.getLogger(__name__)

def run_server(args: argparse.Namespace):
  host = args.host
  port = args.port
  ollama_base_url = args.ollama_host
  ollama_model = args.ollama_model

  capabilities = AgentCapabilities()
  skill = AgentSkill(
    id="blp_a2a_get_ticker_data",
    name="Get ticker data from Bloomberg",
    description="Gets ticker data from Bloomberg given a prompt",
    tags=["ticker", "Bloomberg", "finance", "stock price"],
    examples=["What is the current stock price of Apple?"]
  )
  agent_card = AgentCard(
    name="Bloomberg data Agent",
    description="Helps retrieve data from Bloomberg",
    url=f"http://{host}:{port}",
    version="0.1.0",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=[],
    capabilities=capabilities,
    skills=[skill]
  )
  task_manager = BlpA2ATaskManager()

  server = A2AServer(
    agent_card=agent_card,
    task_manager=task_manager,
    host=host,
    port=port,
  )

  @server.app.on_event("startup")
  async def setup_tools():
    await task_manager.setup_tools(ollama_base_url=ollama_base_url, ollama_model=ollama_model)

  logger.info(f"Starting server on {host}:{port}")
  server.start()
