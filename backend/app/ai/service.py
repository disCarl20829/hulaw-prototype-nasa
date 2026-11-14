import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.ai.prompts import HULAWORLD_INSTRUCTIONS
from app.ai.tools import TOOLS
from app.ai.tool_executor import execute_tool


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 3
MAX_TOOL_OUTPUT_CHARS = 16000

AGENT_INSTRUCTIONS = HULAWORLD_INSTRUCTIONS + """

NASA TOOL RULES:

- Retrieve data using the approved NASA tools.
- If the user explicitly requests multiple datasets,
  retrieve each one before generating the final answer.
- Do not claim a dataset is unavailable unless its
  tool returned an error or missing observations.
- Never invent NASA measurements.
- Never claim you checked a tool that was not called.
- Do not say "I will now check" in a final response.
- Report source names and observation dates.
- Distinguish observations from hypotheses.
- Different indicators have different resolutions.
- Rainfall deficits alone do not establish drought.
- Vegetation greenness alone does not establish health.
- Keep the final explanation concise.
"""


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
        timeout=60.0,
        max_retries=1
    )


def detect_required_tools(message: str) -> list[str]:
    """
    Identify datasets explicitly requested by the user.

    The AI still chooses date parameters, but cannot
    skip a dataset specifically requested in the question.
    """

    text = message.lower()
    required = []

    if re.search(
        r"\brainfall\b|\bprecipitation\b|\bnasa power\b",
        text
    ):
        required.append("get_rainfall_timeline")

    if re.search(
        r"\bsoil moisture\b|\bsmap\b",
        text
    ):
        required.append("get_soil_moisture_history")

    if re.search(
        r"\bvegetation\b|\bndvi\b|\bevi\b|\bmodis\b",
        text
    ):
        required.append("get_vegetation_history")

    return required[:MAX_TOOL_CALLS]


async def ask_hulaworld(
    message: str,
    latitude: float | None = None,
    longitude: float | None = None
) -> dict:

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not deployment:
        raise RuntimeError(
            "Azure AI deployment name is missing."
        )

    if (latitude is None) != (longitude is None):
        raise ValueError(
            "Provide both latitude and longitude."
        )

    has_location = (
        latitude is not None
        and longitude is not None
    )

    # General questions must not trigger NASA tools
    # when no geographic coordinates are supplied.
    required_tools = (
        detect_required_tools(message)
        if has_location else []
    )

    location_context = (
        f"\nSelected map location: "
        f"latitude={latitude}, longitude={longitude}."
        if has_location else
        "\nNo map coordinates were provided. "
        "Ask for a location if measurements are needed."
    )

    input_items = [
        {
            "role": "user",
            "content": message + location_context
        }
    ]

    tools_used = []
    failed_tools = []
    attempted_tools = set()

    client = get_azure_client()

    async with client:

        async def request_model(tool_choice):
            response = await client.responses.create(
                model=deployment,
                instructions=AGENT_INSTRUCTIONS,
                input=input_items,
                tools=TOOLS if has_location else [],
                tool_choice=tool_choice,
                parallel_tool_calls=False,
                max_output_tokens=650,
                store=False
            )

            # Preserve all model output items for
            # the next stateless API request.
            input_items.extend(
                item.model_dump(exclude_none=True)
                for item in response.output
            )

            return response

        async def process_calls(
            response,
            expected_name=None
        ):
            calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            for call in calls:

                if (
                    len(attempted_tools) >= MAX_TOOL_CALLS
                    or call.name in attempted_tools
                ):
                    result = {
                        "status": "error",
                        "message": (
                            "Tool-call limit reached or "
                            "tool already attempted."
                        )
                    }

                elif (
                    expected_name is not None
                    and call.name != expected_name
                ):
                    result = {
                        "status": "error",
                        "message": "Unexpected tool selected."
                    }

                else:
                    attempted_tools.add(call.name)

                    try:
                        arguments = json.loads(
                            call.arguments
                        )

                        if not isinstance(arguments, dict):
                            raise ValueError(
                                "Invalid tool arguments"
                            )

                        # Frontend-selected coordinates
                        # override model-generated ones.
                        arguments["latitude"] = latitude
                        arguments["longitude"] = longitude

                        result = await execute_tool(
                            call.name,
                            arguments
                        )

                    except (ValueError, TypeError, KeyError):
                        result = {
                            "status": "error",
                            "message": (
                                "Invalid date range or "
                                "tool arguments."
                            )
                        }

                    except Exception:
                        logger.exception(
                            "Hulaworld NASA tool error"
                        )

                        result = {
                            "status": "error",
                            "message": (
                                "Environmental data retrieval "
                                "failed."
                            )
                        }

                serialized = json.dumps(
                    result,
                    default=str,
                    allow_nan=False
                )

                if len(serialized) > MAX_TOOL_OUTPUT_CHARS:
                    result = {
                        "status": "error",
                        "message": (
                            "Data response too large. "
                            "Use a shorter period."
                        )
                    }

                    serialized = json.dumps(result)

                # Only count successful, usable results.
                success = (
                    isinstance(result, dict)
                    and result.get("status")
                    not in {"error", "unavailable"}
                    and (
                        (
                            call.name == "get_rainfall_timeline"
                            and bool(result.get("timeline"))
                        )
                        or (
                            call.name == "get_soil_moisture_history"
                            and any(
                                obs.get("status") == "valid"
                                and obs.get("soil_moisture") is not None
                                for obs in result.get(
                                    "observations", []
                                )
                                if isinstance(obs, dict)
                            )
                        )
                        or (
                            call.name == "get_vegetation_history"
                            and any(
                                obs.get("status") == "valid"
                                and (
                                    obs.get("ndvi") is not None
                                    or obs.get("evi") is not None
                                )
                                for obs in result.get(
                                    "observations", []
                                )
                                if isinstance(obs, dict)
                            )
                        )
                    )
                )

                if success:
                    if call.name not in tools_used:
                        tools_used.append(call.name)

                else:
                    if call.name not in failed_tools:
                        failed_tools.append(call.name)

                input_items.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": serialized
                })

            return bool(calls)

        # -----------------------------------
        # MULTI-DATASET MODE
        # -----------------------------------

        if required_tools:

            for name in required_tools:

                # Force the specifically requested tool.
                response = await request_model({
                    "type": "function",
                    "name": name
                })

                called = await process_calls(
                    response,
                    expected_name=name
                )

                if not called:
                    failed_tools.append(name)

            # All requested sources were attempted.
            # Generate the final comparison now.
            response = await request_model("none")

        # -----------------------------------
        # GENERAL / AUTOMATIC MODE
        # -----------------------------------

        else:

            response = await request_model(
                "auto" if has_location else "none"
            )

            if has_location:
                for _ in range(MAX_TOOL_CALLS):

                    called = await process_calls(response)

                    if not called:
                        break

                    if (
                        len(attempted_tools)
                        >= MAX_TOOL_CALLS
                    ):
                        response = await request_model("none")
                        break

                    response = await request_model("auto")

    reply = (
        response.output_text.strip()
        or "Hulaworld could not complete the analysis."
    )

    return {
        "agent": "Hulaworld",
        "reply": reply,
        "tools_used": tools_used
    }
