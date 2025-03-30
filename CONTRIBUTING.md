# Contributing to AI Code Reviewer

Hey there! Thanks for checking out **AI Code Reviewer**, an open-source tool by [AnyMaint](https://anymaint.com). We’re a small startup building tools to simplify maintenance workflows, and we’d love your help to make this project even better. Whether you’re fixing bugs, adding features, or just sharing ideas, every contribution counts!

## How Can You Help?
- **Report Bugs**: Found something broken? Open an issue.
- **Suggest Features**: Got an idea (e.g., a new LLM)? Let us know!
- **Submit Code**: Fix a bug or add a feature via a pull request (PR).
- **Improve Docs**: Tweak this file, the README, or add examples.

## Getting Started
1. **Fork the Repo**:
    - Click "Fork" on [github.com/AnyMaint/code-reviewer](https://github.com/AnyMaint/code-reviewer).
2. **Clone Your Fork**:
```bash
git clone https://github.com/Anymaint/code-reviewer.git
cd code-reviewer
```
3. **Set Up Locally**:
- Install dependencies:
  ```
  pip install -r requirements.txt
  ```
- Set environment variables (see [README.md](README.md)):
  ```
  export GITHUB_TOKEN="your-github-token"
  export OPENAI_API_KEY="your-openai-key"
  export GOOGLE_API_KEY="your-google-key"
  ```
4. **Test It**:
- Run `python review.py AnyMaint/repo 1` to ensure it works.

## Contribution Guidelines
- **Issues**:
    - Check existing issues first to avoid duplicates.
    - Use a clear title (e.g., “Bug: Crash on empty diff”) and describe the problem or idea.
- **Pull Requests**:
    - Work in a branch: `git checkout -b feature/your-idea`.
    - Keep changes focused (one fix/feature per PR).
    - Follow Python’s PEP 8 style (e.g., 4-space indents).
    - Test your changes locally before submitting.
    - Reference any related issue (e.g., “Fixes #12”).
- **Code Style**:
    - Stick to the existing structure (e.g., LLM interface).
    - Add comments for complex logic.

## Our Process
- We’ll review issues and PRs as soon as we can (we’re a small team, so bear with us!).
- If it’s a good fit, we’ll merge it and give you a shoutout in the commit or docs.
- Questions? Ping us in the issue/PR or usimg a contact form on our [website](https://anymaint.com) .

## Ideas to Start
- Add support for more LLMs (e.g., LLaMA, Grok).
- Improve diff parsing for tricky cases.
- Write more usage examples for the README.
- Add support for GitLab or Bitbucket.

Thanks for joining us on this journey—let’s make code reviews awesome together!
