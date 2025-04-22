# AI Code Reviewer
*Automate Pull Request Reviews with ChatGPT, Grok & Gemini*

![BSD 3-Clause License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)
![GitHub Stars](https://img.shields.io/github/stars/AnyMaint/code-reviewer?style=social)
![GitHub Forks](https://img.shields.io/github/forks/AnyMaint/code-reviewer?style=social)

Welcome to **AI Code Reviewer**, a Python tool built by [AnyMaint](https://anymaint.com) to streamline code reviews using large language models (LLMs). Catch issues, summarize PRs, and even comment directly on GitHub—all powered by ChatGPT, Grok or Gemini. We’re open-sourcing this to share with the community and grow our startup’s footprint!

## Features
- **General Overview**: Get a high-level summary of what a PR does, based on its description and changes.
- **Issue Detection**: Identify potential problems in diffs (ignores unchanged code by default).
- **PR Comments**: Automatically post issues as inline comments on open pull requests.
- **Multi-LLM Support**: Switch between ChatGPT, Grok and Gemini with a simple flag.

## Installation
1. Clone the repo:
```bash
   git clone https://github.com/AnyMaint/code-reviewer.git
   cd code-reviewer
```
2. Install dependencies:
```bash
   pip install -r requirements.txt
```
3. Set environment variables:
```bash
   export GITHUB_TOKEN="your-github-token"  # 
   export OPENAI_API_KEY="your-openai-key"  # For ChatGPT
   export GOOGLE_API_KEY="your-google-key"  # For Gemini
   export XAI_API_KEY="your-google-key"     # For Grok
```
## Usage

There is an article how to use the tool. 
It may be outdated, but it is a good start: [How to Use AI Code Reviewer](https://medium.com/itnext/ai-code-reviewer-automate-your-code-reviews-137bfaa20e8b)
- **General PR Summary**:
```bash
   python main.py --repo "owner/repo" --pr 123
```
- **List Issues Only Using Grok**:
```bash
   python main.py --repo "owner/repo" --pr 123 --mode issues --llm grok
```
- **Post Comments to PR in GitHub with Gemini**:
```bash
   python main.py --repo "owner/repo" --pr 123 --mode comments --llm gemini
```
- Add `--full-context` to include whole files, or `--debug` to see LLM requests.

## Contributing
We’re a small startup and love community help! Fork it, fix it, PR it—see [CONTRIBUTING.md](CONTRIBUTING.md) for details. Found a bug? Open an issue!

## About AnyMaint
[AnyMaint](https://anymaint.com) delivers a web-based CMMS for maintenance management, blending machine learning with modular design to monitor equipment, schedule calibrations, and optimize workflows. Tailored for industries like pharmaceuticals and medical devices, we simplify data-driven decisions for production floors.

## License
Licensed under the [BSD 3-Clause License](LICENSE) - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Built with inspiration from Grok at xAI.
- Powered by ChatGPT (OpenAI), Grok (X) and Gemini (Google).

