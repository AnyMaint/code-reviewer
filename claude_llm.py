from llm_interface import LLMInterface, ModelResult
import logging
import os
import anthropic
from typing import Optional
from config import LOG_CHAR_LIMIT

class ClaudeLLM(LLMInterface):
    def __init__(self):
        """
        Initialize Claude LLM client.
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens in response (default: 8192)
        """
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", 8192))
        self.client = anthropic.Anthropic(api_key=self.api_key)        
        
    
    def answer(self, system_prompt: str, user_prompt: str, content: str) -> ModelResult:
        """
        Generate a response using Claude API.
        
        Args:
            system_prompt: System instructions for the model
            user_prompt: User's question or instruction
            content: Additional content to process
            
        Returns:
            ModelResult containing response and token usage information
        """
        logging.debug(
            f"Claude Request:\nModel: {self.model}\nSystem Prompt: {system_prompt[:LOG_CHAR_LIMIT]}..."
            f"\nUser Prompt: {user_prompt[:LOG_CHAR_LIMIT]}...\nContent: {content[:LOG_CHAR_LIMIT]}... (truncated)"
        )

        try:
            # Combine user prompt and content
            full_user_message = f"{user_prompt}\n\nContent:\n{content}" if content else user_prompt
            
            # Make API call to Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,                
                system=system_prompt,
                temperature=0.0,
                messages=[
                    {
                        "role": "user",
                        "content": full_user_message
                    }
                ]
            )
            
            # Extract response text
            response_text = ""
            for content_block in response.content:
                if content_block.type == "text":
                    response_text += content_block.text
            
            # Extract token usage information
            usage = response.usage
            
            return ModelResult(
                response=response_text,
                total_tokens=usage.input_tokens + usage.output_tokens,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens
            )
            
        except Exception as e:
            # Return error information in case of API failure
            logging.error(f"Claude API error: {str(e)}")
            return ModelResult(
                response=f"Error: {str(e)}",
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0
            )