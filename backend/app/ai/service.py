import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.ai.prompts import HULAWORLD_INSTRUCTIONS

BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")


def get_azure_client():
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    base_url = os.getenv("AZURE_OPENAI_BASE_URL")

    if not api_key or not base_url:
        raise RuntimeError(
            "Azure AI configuration is missing."
        )

    if not base_url.startswith("https://"):
        raise RuntimeError(
            "Azure AI endpoint must use HTTPS."
        )

    if not base_url.rstrip("/").endswith("/openai/v1"):
        raise RuntimeError(
            "Expected an Azure OpenAI v1 base URL."
        )

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=30.0,
        max_retries=1
    )


async def ask_hulaworld(message: str) -> str:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not deployment:
        raise RuntimeError(
            "Azure AI deployment name is missing."
        )

    client = get_azure_client()

    async with client:
        response = await client.responses.create(
            model=deployment,
            instructions=HULAWORLD_INSTRUCTIONS,
            input=message,
            max_output_tokens=300,
            store=False
        )

    return (
        response.output_text.strip()
        or "Hulaworld could not generate an answer."
    )
