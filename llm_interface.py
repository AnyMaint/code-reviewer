from abc import ABC, abstractmethod

class LLMInterface(ABC):
    @abstractmethod
    def answer(self, system_prompt: str, user_prompt: str, content: str) -> str:
        """Generate a JSON response for the given prompts and content."""
        pass