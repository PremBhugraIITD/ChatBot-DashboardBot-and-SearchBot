
from universal_mcp.servers import SingleMCPServer
from universal_mcp.integrations import AgentRIntegration
from universal_mcp.stores import EnvironmentStore
import os

from app import CalendlyApp

env_store = EnvironmentStore()
integration_instance = AgentRIntegration(
    name="calendly", 
    store=env_store,
    api_key=os.getenv("AGENTR_API_KEY"),
    base_url=os.getenv("AGENTR_BASE_URL")
)
app_instance = CalendlyApp(integration=integration_instance)

mcp = SingleMCPServer(
    app_instance=app_instance,
)

if __name__ == "__main__":
    mcp.run()


