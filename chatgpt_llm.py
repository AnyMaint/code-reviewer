import logging
import os
import openai
from llm_interface import LLMInterface

class ChatGPTLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for ChatGPT")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def answer(self, system_prompt: str, user_prompt: str, content: str) -> str:
        """Generate a JSON response for the given prompts and content."""
        logging.debug(
            f"ChatGPT Request:\nModel: {self.model}\nSystem Prompt: {system_prompt[:500]}..."
            f"\nUser Prompt: {user_prompt[:500]}...\nContent: {content[:500]}... (truncated)"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + "\n" + content if user_prompt else content},
                ],
                temperature=0.0,
            )
            raw_response = response.choices[0].message.content.strip()
            logging.debug(f"Raw Response:\n{raw_response[:500]}... (truncated)")
            return raw_response
        except Exception as e:
            print(f"Error communicating with ChatGPT API: {str(e)}")
            return ""