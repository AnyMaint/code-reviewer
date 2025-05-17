import logging
import os
import openai
from llm_interface import LLMInterface, ModelResult
from config import LOG_CHAR_LIMIT

class ChatGPTLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for ChatGPT")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def answer(self, system_prompt: str, user_prompt: str, content: str) -> ModelResult:
        """Generate a JSON response for the given prompts and content."""
        logging.debug(
            f"ChatGPT Request:\nModel: {self.model}\nSystem Prompt: {system_prompt[:LOG_CHAR_LIMIT]}..."
            f"\nUser Prompt: {user_prompt[:LOG_CHAR_LIMIT]}...\nContent: {content[:LOG_CHAR_LIMIT]}... (truncated)"
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
            usage = response.usage            
            logging.debug(f"Raw Response:\n{raw_response[:LOG_CHAR_LIMIT]}... (truncated)")
            return ModelResult(response =raw_response, 
                              total_tokens=usage.total_tokens,
                              prompt_tokens=usage.prompt_tokens,
                              completion_tokens=usage.completion_tokens)
        except Exception as e:
            print(f"Error communicating with ChatGPT API: {str(e)}")
            return None
