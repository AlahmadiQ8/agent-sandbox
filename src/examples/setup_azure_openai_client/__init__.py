from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import os
from agents import set_default_openai_client

load_dotenv()

model_name = "gpt-4.1"

# Create OpenAI client using Azure OpenAI
openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

set_default_openai_client(client=openai_client, use_for_tracing=False)
