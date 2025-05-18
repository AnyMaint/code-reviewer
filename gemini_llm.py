import logging
import os
import google.generativeai as genai
from llm_interface import LLMInterface, ModelResult
from config import LOG_CHAR_LIMIT


class GeminiLLM(LLMInterface):
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

    def answer(self, system_prompt: str, user_prompt: str, content: str) -> ModelResult:
        """Generate a response for the given prompts and content."""
        full_input = f"{system_prompt}\n\n{user_prompt}\n\n{content}" if user_prompt else f"{system_prompt}\n\n{content}"
        logging.debug(
            f"Gemini Request:\nModel: {self.model.model_name}\nContent: {full_input[:LOG_CHAR_LIMIT]}... (truncated)")

        try:
            response = self.model.generate_content(
                full_input,
                generation_config={
                    "temperature": 0.0  # Maximum consistency
                }
            )
            raw_response = response.text.strip()
            if response.usage_metadata is None:
                usage = {
                    "total_token_count": 0,
                    "prompt_token_count": 0,
                    "candidates_token_count": 0
                }
            else:
                usage = response.usage_metadata
            logging.debug(f"Raw Response:\n{raw_response[:LOG_CHAR_LIMIT]}... (truncated)")            
            return ModelResult(response=raw_response, 
                             total_tokens=usage.total_token_count,
                             prompt_tokens=usage.prompt_token_count,
                             completion_tokens=usage.candidates_token_count)
        except Exception as e:
            logging.error(f"Error communicating with Gemini API: {str(e)}")            
            return None
