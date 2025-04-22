# grok_llm.py
import os
import requests
from llm_interface import LLMInterface
from prompts import get_prompt

class GrokLLM(LLMInterface):
    def __init__(self, debug: bool = False, deep: bool = False):
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable is required for Grok")
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        self.endpoint = "/chat/completions"
        self.model = os.getenv("GROK_MODEL", "grok-3-latest")
        self.debug = debug
        self.deep = deep
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _get_prompt(self, mode: str) -> str:
        return get_prompt(mode, self.deep)

    def generate_review(self, content: str, mode: str) -> str:
        prompt = self._get_prompt(mode)

        if self.debug:
            print(f"Grok Request:\nModel: {self.model}\nPrompt: {prompt}\nContent: {content[:500]}... (truncated)")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            "temperature": 0.0  # Maximum consistency
        }

        try:
            response = requests.post(f"{self.base_url}{self.endpoint}", headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Grok API HTTP Error: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Grok API Request Error: {e}")
        except KeyError as e:
            raise ValueError(f"Unexpected response format from Grok API: {e}")
