__version__ = "2.0.1"

import argparse
import logging
from chatgpt_llm import ChatGPTLLM
from gemini_llm import GeminiLLM
from github_vcsp import GithubVCSP
from gitlab_vcsp import GitlabVCSP
from bitbucket_vcsp import BitbucketVCSP
from grok_llm import GrokLLM
from models import LLMReviewResult, CodeReview
from llm_code_reviewer import LLMCodeReviewer

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AI Code Review for PRs/MRs")
parser.add_argument("repository", help="Repository name (e.g., 'username/repo')")
parser.add_argument("pr_number", type=int, help="Pull Request number")
parser.add_argument(
    "--mode",
    choices=["issues", "comments"],
    default="issues",
    help="Mode: 'issues' (issues only), 'comments' (issues as PR comments)",
)
parser.add_argument(
    "--full-context",
    action="store_true",
    default=False,
    help="Send full files with diffs to the LLM (default: diffs only)",
)
parser.add_argument(
    "--llm",
    choices=["chatgpt", "gemini", "grok"],
    default="chatgpt",
    help="LLM to use: 'chatgpt', 'gemini', or 'grok' (default: chatgpt)",
)
parser.add_argument(
    "--deep",
    action="store_true",
    default=False,
    help="Enable deep mode for verbose reviews including non-bug feedback",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging for LLM API requests and responses",
)
parser.add_argument(
    "--version",
    action="version",
    version=f"AI Code Reviewer {__version__}",
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
    logging.getLogger("openai").setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.DEBUG)
else:
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# LLM setup
llm_map = {
    "chatgpt": ChatGPTLLM,
    "gemini": GeminiLLM,
    "grok": GrokLLM,
}
try:
    llm = llm_map[args.llm]()
except ValueError as e:
    logging.error(f"Failed to initialize LLM: {str(e)}")
    exit(1)

# VCS setup
version_control_system_map = {
    "github": GithubVCSP,
    "gitlab": GitlabVCSP,
    "bitbucket": BitbucketVCSP,
}
try:
    vcsp = version_control_system_map[args.vcsp]()
except ValueError as e:
    logging.error(f"Failed to initialize VCS: {str(e)}")
    exit(1)

# Fetch repository and pull request
try:
    pr = vcsp.get_pull_request(args.repository, args.pr_number)
except Exception as e:
    logging.error(f"Failed to fetch pull request: {str(e)}")
    exit(1)

# Create LLMCodeReviewer
reviewer = LLMCodeReviewer(
    llm=llm,
    vcsp=vcsp,
    full_context=args.full_context,
    deep=args.deep,
)

# Get the review
try:
    review_result: LLMReviewResult = reviewer.review_pr(pr, args.repository, args.pr_number)
except Exception as e:
    logging.error(f"Failed to generate review: {str(e)}")
    exit(1)

print("Code Issues:")
if not review_result.reviews:
    print("  No issues found.")
for review in review_result.reviews:
    print(f"  File: {review.file}, Line: {review.line}")
    if review.comments:
        for comment in review.comments:
            print(f"    - {comment}")
    else:
        print("    - No issues found.")

if args.mode == "comments" and pr.state.lower() == "open":
    try:
        head_commit = vcsp.get_commit(args.repository, pr.head_sha)
    except Exception as e:
        logging.error(f"Failed to fetch head commit: {str(e)}")
        exit(1)
    for review in review_result.reviews:
        if review.comments:
            comment = (
                f"AI Issue by {args.llm} (full-context: {args.full_context}, deep: {args.deep}):\n"
                + "\n".join(review.comments)
            )
            try:
                vcsp.create_review_comment(
                    repo_name=args.repository,
                    comment=comment,
                    commit=head_commit.sha,
                    file_path=review.file,
                    line=review.line,
                    side="RIGHT",
                )
                logging.info(f"Posted comment on {review.file} at line {review.line}")
            except Exception as e:
                logging.error(f"Error posting comment on {review.file}: {str(e)}")
elif args.mode == "comments":
    logging.info("Comments mode: PR is closed, no comments posted.")