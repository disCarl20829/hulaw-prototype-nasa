import asyncio
import sys
from pathlib import Path

from openai import APIStatusError, APIConnectionError

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.ai.service import ask_hulaworld

async def main():
    print("HULAWORLD — AZURE AI TEST")
    print("-" * 35)

    try:
        response = await ask_hulaworld(
            "What is agricultural drought?"
        )

        print("STATUS: SUCCESS")
        print("Hulaworld:", response)

    except APIStatusError as error:
        print("STATUS: AZURE API ERROR")
        print("HTTP status:", error.status_code)

        try:
            details = error.response.json()
            info = details.get("error", {})
            if isinstance(info, dict):
                print("Error code:", info.get("code"))
                print("Error type:", info.get("type"))
        except ValueError:
            pass

    except APIConnectionError:
        print("STATUS: CONNECTION ERROR")

    except RuntimeError as error:
        print("STATUS: CONFIGURATION ERROR")
        print(str(error))


if __name__ == "__main__":
    asyncio.run(main())
