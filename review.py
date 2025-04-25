# review.py
__version__ = "1.1.1"

import argparse
import re
from chatgpt_llm import ChatGPTLLM
from gemini_llm import GeminiLLM
from github_vcsp import GithubVCSP
from gitlab_vcsp import GitlabVCSP
from grok_llm import GrokLLM

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AI Code Review for PRs/MRs")
parser.add_argument("repository", help="Repository name (e.g., 'username/repo')")
parser.add_argument("pr_number", type=int, help="Pull Request number")
parser.add_argument("--mode", choices=["general", "issues", "comments"], default="general",
                    help="Mode: 'general' (PR overview), 'issues' (issues only), 'comments' (issues as PR comments)")
parser.add_argument("--full-context", action="store_true", default=False,
                    help="Send full files with diffs to the LLM (default: diffs only)")
parser.add_argument("--llm", choices=["chatgpt", "gemini", "grok"], default="chatgpt",
                    help="LLM to use: 'chatgpt', 'gemini', or 'grok' (default: chatgpt)")
parser.add_argument("--deep", action="store_true", default=False,
                    help="Enable deep mode for verbose reviews including non-bug feedback")
parser.add_argument("--debug", action="store_true", help="Print LLM API request details")
parser.add_argument("--version", action="version", version=f"AI Code Reviewer {__version__}",
                    help="Show the version and exit")
# add vcs
parser.add_argument("--vcsp", choices=["github", "gitlab"], default="github",
                    help="Version control system provider to use: 'github' (default: github)")

args = parser.parse_args()


# LLM setup
llm_map = {
    "chatgpt": ChatGPTLLM,
    "gemini": GeminiLLM,
    "grok": GrokLLM
}

llm = llm_map[args.llm](debug=args.debug, deep=args.deep)

# VCS setup
version_control_system_map = {
    "github": GithubVCSP,
    "gitlab": GitlabVCSP,
}
vcsp = version_control_system_map[args.vcsp]()

# Fetch repository and pull request
pr = vcsp.get_pull_request(args.repository, args.pr_number)

# Function to parse diff and get file line number (for comments mode)
def get_file_line_from_diff(diff):
    lines = diff.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line)
            if match:
                new_start = int(match.group(3))  # Start line in the new file
                for j, diff_line in enumerate(lines[i+1:], start=1):
                    if diff_line.startswith("+") and not diff_line.startswith("+++"):
                        return new_start + j - 1  # Adjust for zero-based counting
    return 1  # Fallback if no valid line found

# Prepare PR title and description for all modes
pr_title = pr.title or "No title provided"
pr_description = pr.body or "No description provided"
base_content = f"PR Title: {pr_title}\nPR Description:\n{pr_description}\n\n"

# Prepare content based on mode and full-context flag
pr_files = vcsp.get_files_in_pr(args.repository, args.pr_number)
if args.full_context:
    all_content = []
    for file in pr_files:
        if file.patch:
            file_content = vcsp.get_file_content(args.repository, file.filename, ref=pr.head_sha).decoded_content.decode("utf-8")
            all_content.append(f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}\n{'-' * 16}")
    diff_content = "\n\n".join(all_content)
else:
    diff_content = "\n".join([file.patch + "\n" + "-" * 16 for file in pr_files if file.patch])

# Combine PR title, description, and diffs for all modes
content = base_content
if args.mode == "general":
    content += "Diffs:\n" + diff_content
elif args.mode in ["issues", "comments"]:
    content += "Diffs:\n" + diff_content

# Get the review
review_text = llm.generate_review(content, args.mode)

# Process based on mode
if args.mode == "general":
    print(f"General PR Review:\n{review_text}")

elif args.mode == "issues":
    print(f"Code Issues:\n{review_text}")

elif args.mode == "comments":
    print(f"Code Issues:\n{review_text}")
    if pr.state == "open":
        head_commit = vcsp.get_commit(args.repository, pr.head_sha)
        for file in pr_files:
            if file.patch:
                file_content = vcsp.get_file_content(args.repository, file.filename, ref=pr.head_sha).decoded_content.decode("utf-8") if args.full_context else ""
                diff = file.patch
                # Include PR title and description in each chunk
                file_chunk_base = f"PR Title: {pr_title}\nPR Description:\n{pr_description}\n\n"
                chunk = file_chunk_base + (f"File: {file.filename}\n{file_content}\n\nDiff:\n{diff}" if args.full_context else f"Diff:\n{diff}")
                file_review = llm.generate_review(chunk, args.mode)

                if file_review and "no feedback" not in file_review.lower():
                    line_num = get_file_line_from_diff(diff)
                    comment = f"AI Issue: {file_review}"
                    try:
                        vcsp.create_review_comment(
                            repo_name=args.repository,
                            comment=comment,
                            commit=head_commit.sha,
                            file_path=file.filename,
                            line=line_num,
                            side="RIGHT"
                        )
                        print(f"Posted comment on {file.filename} at line {line_num}: {comment}")
                    except Exception as e:
                        print(f"Error posting comment on {file.filename}: {str(e)}")
    else:
        print("Comments mode: PR is closed, no comments posted.")
