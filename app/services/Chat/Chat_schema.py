
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

class FirecommChatRequestSchema(BaseModel):
    type: Literal["text", "audio"]    
    user_input: Optional[str] = Field(
        None, 
        description="User input text"
    )
    @model_validator(mode="after")
    def validate_inputs(self):
        if self.type == "text" and not self.user_input:
            raise ValueError("user_input is required when type='text'")
        return self
