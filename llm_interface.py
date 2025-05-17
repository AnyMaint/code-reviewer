from abc import ABC, abstractmethod
from dataclasses import dataclass



@dataclass
class ModelResult:
    response: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


class LLMInterface(ABC):
    @abstractmethod
    def answer(self, system_prompt: str, user_prompt: str, content: str) -> ModelResult:
        """Generate a JSON response for the given prompts and content."""
        pass