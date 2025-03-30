import os
import argparse
from github import Github
import openai
import re

# Prompt constants
GENERAL_PROMPT = (
    "You are a code reviewer. This input includes a PR description and git diffs "
    "(and optionally whole files for context). Provide a general overview of what "
    "this PR attempts to do based on its description and changes:"
)
ISSUES_PROMPT = (
    "You are a code reviewer. This input includes git diffs (and optionally whole "
    "files for context). List only code issues or potential problems found in the "
    "diffs, ignoring unchanged code in whole files unless it directly affects the diff. "
    "Do not praise what’s good:"
)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AI Code Review for GitHub PRs")
parser.add_argument("repository", help="Repository name (e.g., 'username/repo')")
parser.add_argument("pr_number", type=int, help="Pull Request number")
parser.add_argument("--mode", choices=["general", "issues", "comments"], default="general",
                    help="Mode: 'general' (PR overview), 'issues' (issues only), 'comments' (issues as PR comments)")
parser.add_argument("--full-context", action="store_true", default=False,
                    help="Send full files with diffs to OpenAI (default: diffs only)")
parser.add_argument("--debug", action="store_true", help="Print OpenAI API request details")
args = parser.parse_args()

# Fetch values from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini

# Validate environment variables
if not all([GITHUB_TOKEN, OPENAI_API_KEY]):
    raise ValueError("Missing required environment variables: GITHUB_TOKEN or OPENAI_API_KEY")

# GitHub setup
g = Github(GITHUB_TOKEN)
repo = g.get_repo(args.repository)
pr = repo.get_pull(args.pr_number)

# OpenAI setup
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Function to get the prompt based on mode
def get_prompt(mode):
    if mode == "general":
        return GENERAL_PROMPT
    elif mode in ["issues", "comments"]:
        return ISSUES_PROMPT
    raise ValueError(f"Unknown mode: {mode}")

# Function to get AI review for a code chunk
def get_ai_review(code_chunk, mode):
    prompt = get_prompt(mode)

    if args.debug:
        print(f"OpenAI Request:\nModel: {OPENAI_MODEL}\nPrompt: {prompt}\nContent: {code_chunk[:500]}... (truncated)")

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": code_chunk}
        ],
        temperature=0.0  # Maximum consistency
        # max_tokens omitted for unlimited output (up to model limit, e.g., 4096 for gpt-4o-mini)
    )
    return response.choices[0].message.content.strip()

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

# Prepare content based on mode and full-context flag
if args.mode == "general":
    pr_description = pr.body or "No description provided"
    if args.full_context:
        all_content = [f"PR Description:\n{pr_description}"]
        for file in pr.get_files():
            if file.patch:
                file_content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode("utf-8")
                all_content.append(f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}\n{'-' * 16}")
        content = "\n\n".join(all_content)
    else:
        content = f"PR Description:\n{pr_description}\n\nDiffs:\n" + "\n".join([file.patch + "\n" + "-" * 16 for file in pr.get_files() if file.patch])
elif args.mode in ["issues", "comments"]:
    if args.full_context:
        all_content = []
        for file in pr.get_files():
            if file.patch:
                file_content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode("utf-8")
                all_content.append(f"File: {file.filename}\n{file_content}\n\nDiff:\n{file.patch}\n{'-' * 16}")
        content = "\n\n".join(all_content)
    else:
        content = "\n".join([file.patch + "\n" + "-" * 16 for file in pr.get_files() if file.patch])

# Get the review
review_text = get_ai_review(content, args.mode)

# Process based on mode
if args.mode == "general":
    print(f"General PR Review:\n{review_text}")

elif args.mode == "issues":
    print(f"Code Issues:\n{review_text}")

elif args.mode == "comments":
    print(f"Code Issues:\n{review_text}")
    if pr.state == "open":
        head_commit = repo.get_commit(pr.head.sha)
        for file in pr.get_files():
            if file.patch:
                file_content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode("utf-8") if args.full_context else ""
                diff = file.patch
                chunk = f"File: {file.filename}\n{file_content}\n\nDiff:\n{diff}" if args.full_context else diff
                file_review = get_ai_review(chunk, args.mode)

                if file_review and "no feedback" not in file_review.lower():
                    line_num = get_file_line_from_diff(diff)
                    comment = f"AI Issue: {file_review}"
                    try:
                        pr.create_review_comment(
                            body=comment,
                            commit=head_commit,
                            path=file.filename,
                            line=line_num,
                            side="RIGHT"
                        )
                        print(f"Posted comment on {file.filename} at line {line_num}: {comment}")
                    except Exception as e:
                        print(f"Error posting comment on {file.filename}: {str(e)}")
