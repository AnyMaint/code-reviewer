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
    level=logging.INFO,
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
    nargs="+",
    help="LLM to use (one or more): 'chatgpt', 'gemini', or 'grok' (default: chatgpt)",
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

for i in range(len(args.llm)):
    try:
        llm = llm_map[args.llm[i]]()
    except ValueError as e:
        logging.error(f"Failed to initialize LLM: {str(e)}")
        continue

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
        continue

    print("Code Issues:")
    if not review_result or not review_result.reviews:
        print("  No issues found.")    
    else:
        review_summary = ""
        for review in review_result.reviews:
            review_summary += f"  File: {review.file}, Line: {review.line}\n"
            if review.comments:
                review_summary += "    Comments: " + '\n'.join(str(comment) for comment in review.comments)
            if review.bug_count != 0:
                review_summary += f"    bugCount={review.bug_count},"
            if review.smell_count != 0:
                review_summary += f"    smellCount={review.smell_count},"
            if review.optimization_count != 0:
                review_summary += f"    optimizationCount={review.optimization_count},"
            if review.logical_errors != 0:
                review_summary += f"    logicalErrors={review.logical_errors}\n"
            if review.performance_issues != 0:
                review_summary += f"    performanceIssues={review.performance_issues},"
        print(review_result.get_overall_review(args.deep, args.full_context, args.llm[i]))
        print(review_summary)
                

    if args.mode == "comments" and pr.state.lower() == "open":
        try:
            head_commit = vcsp.get_commit(args.repository, pr.head_sha)
        except Exception as e:
            logging.error(f"Failed to fetch head commit: {str(e)}")
            exit(1)
        vcsp.create_review_comment(
                        repo_name=args.repository,
                        comment=review_result.get_overall_review(args.deep, args.full_context, args.llm[i]),                        
                        file_path="",
                        line=0,
                        commit=head_commit.sha,
                        side="RIGHT"
                    )
        for review in review_result.reviews:
            if review.comments:
                lines = ["AI Comment:"] + review.comments

                # add any non-zero counts
                if review.bug_count:
                    lines.append(f"    bugCount={review.bug_count}")
                if review.smell_count:
                    lines.append(f"    smellCount={review.smell_count}")
                if review.optimization_count:
                    lines.append(f"    optimizationCount={review.optimization_count}")
                if review.logical_errors:
                    lines.append(f"    logicalErrors={review.logical_errors}")
                if review.performance_issues:
                    lines.append(f"    performanceIssues={review.performance_issues}")

                comment = "\n".join(lines)
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
    break