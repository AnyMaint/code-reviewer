from abc import ABC, abstractmethod

class LLMInterface(ABC):
    @abstractmethod
    def generate_review(self, content: str, mode: str) -> str:
        """Generate a review for the given content and mode."""
        pass
