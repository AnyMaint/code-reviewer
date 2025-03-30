import os
import openai
from llm_interface import LLMInterface
from prompts import GENERAL_PROMPT, ISSUES_PROMPT

class ChatGPTLLM(LLMInterface):
    def __init__(self, debug: bool = False):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for ChatGPT")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.debug = debug

    def _get_prompt(self, mode: str) -> str:
        if mode == "general":
            return GENERAL_PROMPT
        elif mode in ["issues", "comments"]:
            return ISSUES_PROMPT
        raise ValueError(f"Unknown mode: {mode}")

    def generate_review(self, content: str, mode: str) -> str:
        prompt = self._get_prompt(mode)

        if self.debug:
            print(f"ChatGPT Request:\nModel: {self.model}\nPrompt: {prompt}\nContent: {content[:500]}... (truncated)")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            temperature=0.0  # Maximum consistency
            # max_tokens omitted for unlimited output
        )
        return response.choices[0].message.content.strip()

