from openai import AsyncAzureOpenAI
import os
from agents import set_default_openai_client

model_name = "gpt-4.1"

# Create OpenAI client using Azure OpenAI
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if azure_endpoint is None:
    raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set.")

openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=azure_endpoint,
)

set_default_openai_client(client=openai_client, use_for_tracing=False)
