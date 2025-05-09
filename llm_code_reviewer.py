import logging
from typing import Any

from config import LOG_CHAR_LIMIT
from json_cleaner import JsonResponseCleaner
from llm_interface import LLMInterface, ModelResult
from collections import defaultdict
from prompts import get_prompt
from models import LLMReviewResult
import re

from vcsp_interface import VCSPInterface


class LLMCodeReviewer:
    """Handles code review generation by constructing prompts and parsing LLM JSON responses."""

    def __init__(
            self,
            llm: LLMInterface,
            vcsp: VCSPInterface,  # VCS interface (e.g., GithubVCSP); type depends on implementation
            full_context: bool = False,
            deep: bool = False
    ):
        self.llm = llm
        self.vcsp = vcsp
        self.full_context = full_context
        self.deep = deep
        self.json_cleaner = JsonResponseCleaner()

    def review_pr(self, pr: Any, repository: str, pr_number: int) -> LLMReviewResult:
        """
        Generate a code review for the given PR, returning JSON-based results.

        Args:
            pr: The pull request object from the VCS.
            repository: The repository name (e.g., 'username/repo').
            pr_number: The pull request number.

        Returns:
            LLMReviewResult containing the parsed reviews with adjusted line numbers.
        """
        # Prepare PR title and description
        pr_title = pr.title or "No title provided"
        pr_description = pr.body or "No description provided"
        base_content = f"PR Title: {pr_title}\nPR Description:\n{pr_description}\n\n"

        # Prepare content based on full-context flag
        pr_files = self.vcsp.get_files_in_pr(repository, pr_number)
        all_content = []
        file_patches = {}  # Store patches for line number fallback
        for file in pr_files:
            if file.patch:
                file_patches[file.filename] = file.patch
                if self.full_context:
                    try:
                        file_content = self.vcsp.get_file_content(repository, file.filename, ref=pr.head_sha)
                        file_chunk = f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}"
                    except ValueError as e:
                        logging.error(f"Skipping file {file.filename}: {str(e)}")

                else:
                    file_chunk = f"File: {file.filename}\nDiff:\n{file.patch}"
                all_content.append(file_chunk)
        diff_content = "\n\n".join(all_content)

        # Combine PR title, description, and diffs
        content = base_content + "Diffs:\n" + diff_content

        # Get system prompt
        system_prompt = get_prompt(self.deep)

        # Call LLM
        raw_response = self.llm.answer(
            system_prompt=system_prompt,
            user_prompt="",  # No separate user prompt needed; content includes all info
            content=content
        )

        if raw_response:
        # Parse JSON response
            cleaned_response = self.json_cleaner.strip(raw_response.response)
            logging.debug(f"Cleaned Response:\n{cleaned_response[:LOG_CHAR_LIMIT]}... (truncated)")
            if not cleaned_response:
                logging.error("Error: No valid JSON found in LLM response")
                return None
            try:
                review_result = LLMReviewResult.from_json(cleaned_response, 
                    raw_response.total_tokens,raw_response.prompt_tokens, raw_response.completion_tokens)                
                return review_result
            except ValueError as e:
                logging.error(f"Error parsing LLM response: {str(e)}")
        return None
