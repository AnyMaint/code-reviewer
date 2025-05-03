import logging
import os
import requests
from llm_interface import LLMInterface

class GrokLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable is required for Grok")
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        self.endpoint = "/chat/completions"
        self.model = os.getenv("GROK_MODEL", "grok-3-latest")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def answer(self, system_prompt: str, user_prompt: str, content: str) -> str:
        """Generate a response for the given prompts and content."""
        logging.debug(
            f"Grok Request:\nModel: {self.model}\nSystem Prompt: {system_prompt[:500]}..."
            f"\nUser Prompt: {user_prompt[:500]}...\nContent: {content[:500]}... (truncated)"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\n" + content if user_prompt else content},
            ],
            "temperature": 0.0  # Maximum consistency
        }

        try:
            response = requests.post(f"{self.base_url}{self.endpoint}", headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            raw_response = result["choices"][0]["message"]["content"].strip()
            logging.debug(f"Raw Response:\n{raw_response[:500]}... (truncated)")
            return raw_response
        except requests.exceptions.HTTPError as e:
            logging.error(f"Grok API HTTP Error: {e.response.text}")
            return ""
        except requests.exceptions.RequestException as e:
            logging.error(f"Grok API Request Error: {str(e)}")
            return ""
        except KeyError as e:
            logging.error(f"Unexpected response format from Grok API: {str(e)}")
            return ""