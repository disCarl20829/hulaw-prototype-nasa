import logging

from fastapi import APIRouter, HTTPException
from openai import OpenAIError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)

from app.ai.service import ask_hulaworld


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/hulaworld",
    tags=["Hulaworld AI"]
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=1000
    )

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        allow_inf_nan=False
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        allow_inf_nan=False
    )

    @model_validator(mode="after")
    def validate_location(self):
        if (self.latitude is None) != (
            self.longitude is None
        ):
            raise ValueError(
                "Both latitude and longitude are required"
            )

        return self


class ChatResponse(BaseModel):
    agent: str
    reply: str
    tools_used: list[str]


@router.post(
    "/chat",
    response_model=ChatResponse
)
async def chat(request: ChatRequest):
    try:
        result = await ask_hulaworld(
            message=request.message,
            latitude=request.latitude,
            longitude=request.longitude
        )

        return ChatResponse(**result)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid Hulaworld request"
        )

    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Hulaworld AI is not configured"
        )

    except OpenAIError:
        logger.warning(
            "Hulaworld AI provider request failed"
        )

        raise HTTPException(
            status_code=502,
            detail="AI service temporarily unavailable"
        )
