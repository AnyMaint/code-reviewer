from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMInterface(ABC):
    @abstractmethod
    def answer(self, system_prompt: str, user_prompt: str, content: str) -> str:
        """Generate a JSON response for the given prompts and content."""
        pass

@dataclass
class ModelResult:
    response: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int