__version__ = "2.0.1"

import argparse
import logging
from bitbucket_vcsp import BitbucketVCSP
from chatgpt_llm import ChatGPTLLM
from gemini_llm import GeminiLLM
from github_vcsp import GithubVCSP
from gitlab_vcsp import GitlabVCSP
from grok_llm import GrokLLM

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)

system_prompt = """You are experienced programmer and code reviewer."""
user_prompt = """
    Review the provided pull request details, including the PR title, description, and code diffs. 
    Provide a high-level summary of the changes in plain text, explaining their purpose and overall impact. 
    Use the PR description to understand the intent of the changes, and focus on summarizing the diffs as a cohesive set of changes. 
    Do not list changes for individual files or provide file-specific feedback. 
    If the diff is empty, state that no changes were found. 
    If the PR description is missing, base the summary solely on the diffs and title.
    """

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AI PR Description Generator")
parser.add_argument("repository", help="Repository name (e.g., 'username/repo')")
parser.add_argument("pr_number", type=int, help="Pull Request number")
parser.add_argument(
    "--llm",
    choices=["chatgpt", "gemini", "grok"],
    default="chatgpt",
    help="LLM to use: 'chatgpt', 'gemini', or 'grok' (default: chatgpt)",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging for LLM API requests and responses",
)
parser.add_argument(
    "--version",
    action="version",
    version=f"AI PR Description Generator {__version__}",
    help="Show the version and exit",
)
parser.add_argument(
    "--vcsp",
    choices=["github", "gitlab", "bitbucket"],
    default="github",
    help="Version control system provider to use: 'github' (default: github)",
)

args = parser.parse_args()

# Set logging level based on --debug
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# LLM setup
llm_map = {
    "chatgpt": ChatGPTLLM,
    "gemini": GeminiLLM,
    "grok": GrokLLM,
}
llm = llm_map[args.llm]()

# VCS setup
version_control_system_map = {
    "github": GithubVCSP,
    "gitlab": GitlabVCSP,
    "bitbucket": BitbucketVCSP,
}
vcsp = version_control_system_map[args.vcsp]()

# Fetch repository and pull request
try:
    pr = vcsp.get_pull_request(args.repository, args.pr_number)
except Exception as e:
    logging.error(f"Failed to fetch pull request: {str(e)}")
    exit(1)

# Prepare PR title and description
pr_title = pr.title or "No title provided"
pr_description = pr.body or "No description provided"
base_content = f"PR Title: {pr_title}\nPR Description:\n{pr_description}\n\n"

# Prepare content based on diffs
try:
    pr_files = vcsp.get_files_in_pr(args.repository, args.pr_number)
except Exception as e:
    logging.error(f"Failed to fetch PR files: {str(e)}")
    exit(1)

all_content = []
for file in pr_files:
    if file.patch:
        file_chunk = f"File: {file.filename}\nDiff:\n{file.patch}"
        all_content.append(file_chunk)
diff_content = "\n\n".join(all_content)

# Combine PR title, description, and diffs
content = base_content + "Diffs:\n" + diff_content

# Get the review
try:
    review_result = llm.answer(system_prompt, user_prompt, content)
    print(f"General PR Review:\n{review_result}")
except Exception as e:
    logging.error(f"Failed to generate review: {str(e)}")
    exit(1)