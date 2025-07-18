import os
from dotenv import load_dotenv
from server import run_server

# Load environment variables
load_dotenv()

# Get access token
access_token = os.getenv('QB_TIME_ACCESS_TOKEN')
if not access_token:
    raise ValueError("QB_TIME_ACCESS_TOKEN environment variable is required")

# Get environment
node_env = os.getenv('NODE_ENV', 'development')

# Start the server
run_server(access_token, node_env)
