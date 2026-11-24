from typing import Annotated, Optional

from pydantic import BaseModel, Field, StringConstraints

# Whitespace is trimmed first, then the 1-4000 length rule is checked.
Message = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: Message
    system_prompt: Optional[str] = Field(default=None, max_length=4000)
