import re
from typing import Optional


class JsonResponseCleaner:
    """
    Utility class to clean and normalize JSON responses from LLMs.
    Handles common patterns like code blocks and prepares the response for JSON parsing.
    """

    def __init__(self):
        # Define patterns to strip (extensible for future patterns)
        self.patterns = [
            # Pattern for ```json ... ``` or ``` ... ``` code blocks
            (r'```json\s*(.*?)\s*```', r'\1'),
            (r'```\s*(.*?)\s*```', r'\1'),
        ]

    def strip(self, raw_response: str) -> Optional[str]:
        """
        Strip unwanted formatting from the raw LLM response to extract valid JSON.

        Args:
            raw_response: The raw response string from the LLM.

        Returns:
            The cleaned JSON string, or None if cleaning fails or no JSON is found.
        """
        if not raw_response:
            return None

        cleaned_response = raw_response.strip()

        # Apply each pattern to remove unwanted formatting
        for pattern, replacement in self.patterns:
            cleaned_response = re.sub(pattern, replacement, cleaned_response, flags=re.DOTALL)

        # Additional cleanup: remove leading/trailing whitespace and newlines
        cleaned_response = cleaned_response.strip()

        # Basic validation: check if the response looks like JSON (starts with [ or {)
        if not cleaned_response or not (cleaned_response.startswith('[') or cleaned_response.startswith('{')):
            return None

        return cleaned_response
