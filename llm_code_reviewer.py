import logging
from typing import Any

from config import LOG_CHAR_LIMIT, MAX_LENGTH_DIFF, MAX_TOTAL_LENGTH
from json_cleaner import JsonResponseCleaner
from llm_interface import LLMInterface, ModelResult
from collections import defaultdict
from prompts import get_prompt
from models import LLMReviewResult
import re

from vcsp_interface import VCSPInterface

def remove_hunk_counts(diff_text: str) -> str:
    """
    Given a unified diff as a string, remove the comma+count parts
    from hunk header lines:
      @@ -start,count +start,count @@
    becomes
      @@ -start +start @@
    """
    # This regex finds hunk headers, capturing the two start-line numbers
    pattern = re.compile(r'@@ -(\d+),\d+ \+(\d+),\d+ @@')
    # Replace each match with commas removed
    return pattern.sub(r'@@ -\1 +\2 @@', diff_text)

def is_new_file(diff_lines):
    """
    Given the lines of a unified diff for one file,
    return True if it’s a brand-new file.
    """
    for line in diff_lines:
        # Git’s explicit marker
        if line.startswith('new file mode '):
            return True
        # Or the /dev/null trick
        if line.startswith('--- ') and '/dev/null' in line:
            return True
    return False

def is_deleted_file(diff_lines):
    """
    Given the lines of a unified diff for one file,
    return True if it’s a deleted file.
    """
    for line in diff_lines:
        # Git’s explicit marker
        if line.startswith('deleted file mode '):
            return True
        # Or the /dev/null trick on the new side
        if line.startswith('+++ ') and '/dev/null' in line:
            return True
    return False


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
        retry_count = 0
        while retry_count < 2:
            retry_count += 1
            # Prepare PR title and description
            pr_title = pr.title or "No title provided"
            pr_description = pr.body or "No description provided"
            base_content = f"PR Title: {pr_title}\nPR Description:\n{pr_description}\n\n"

            # Prepare content based on full-context flag
            pr_files = self.vcsp.get_files_in_pr(repository, pr_number)
            
            all_content = [] 
            all_content_length = 0
            for file in pr_files:
                if file.patch and len(file.patch) <= MAX_LENGTH_DIFF:
                    file.patch = remove_hunk_counts(file.patch)
                    if self.full_context and not is_new_file(file.patch) and not is_deleted_file(file.patch):                    
                        try:
                            file_content = self.vcsp.get_file_content(repository, file.filename, ref=pr.head_sha)
                            file_chunk = f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}"
                        except ValueError as e:
                            logging.error(f"Skipping file {file.filename}: {str(e)}")

                    else:
                        file_chunk = f"File: {file.filename}\nDiff:\n{file.patch}"
                    all_content.append(file_chunk)
                    all_content_length += len(file_chunk)
                    if all_content_length > MAX_TOTAL_LENGTH:
                        logging.warning(f"Content length exceeded {MAX_LENGTH_DIFF} characters. Truncating.")
                        break


            diff_content = "\n\n".join(all_content)

            # Combine PR title, description, and diffs
            content = base_content + "Diffs:\n" + diff_content

            # Get system prompt
            system_prompt = get_prompt(self.deep)        
            # Call LLM
            llm_answer = self.llm.answer(
                                system_prompt=system_prompt,
                                user_prompt="",  # No separate user prompt needed; content includes all info
                                content=content
                            ) if all_content_length > 0 else None

            if llm_answer:
                if llm_answer.response == "Long_Request" and self.full_context:
                    self.full_context = False #retrun with less context
                    logging.warning("LLM response indicates request was too long; retrying with less context.")
                    continue  # Retry with reduced context
                retry_count = 2  # Exit retry loop if we got a valid response
                # Parse JSON response
                cleaned_response = self.json_cleaner.strip(llm_answer.response)
                logging.debug(f"Cleaned Response:\n{cleaned_response[:LOG_CHAR_LIMIT]}... (truncated)")
                if not cleaned_response:
                    logging.error("Error: No valid JSON found in LLM response")
                    return None
                try:
                    review_result = LLMReviewResult.from_json(cleaned_response, 
                        llm_answer.total_tokens,llm_answer.prompt_tokens, llm_answer.completion_tokens)                
                    return review_result
                except ValueError as e:
                    logging.error(f"Error parsing LLM response: {str(e)}")
            return None
