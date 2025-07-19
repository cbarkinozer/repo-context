# src/repo_context/cli.py
import argparse
import os
from pathlib import Path
from .core import generate_context_from_repo, COMMON_EXTENSIONS

def main():
    parser = argparse.ArgumentParser(
        prog="repo-context",
        description="Generate an intelligent context snapshot from a GitHub repository."
    )
    parser.add_argument(
        "repo_url",
        help="The full URL of the public or private GitHub repository."
    )
    parser.add_argument(
        "-o", "--output",
        help="The path to the output file. If not provided, prints to standard output.",
        default=None
    )
    parser.add_argument(
        "--token",
        help="Your GitHub Personal Access Token (PAT) for private repositories. "
             "Can also be set via the GITHUB_TOKEN environment variable.",
        default=os.environ.get("GITHUB_TOKEN")
    )
    parser.add_argument(
        "--extensions",
        nargs='+',
        help="A space-separated list of file extensions to include.",
        default=COMMON_EXTENSIONS
    )
    parser.add_argument(
        "--line-limit",
        type=int,
        default=3000,
        help="The maximum number of lines per file. Set to 0 for no limit."
    )

    args = parser.parse_args()

    print("Generating intelligent context...")

    full_context = generate_context_from_repo(
        repo_url=args.repo_url,
        selected_extensions=args.extensions,
        file_line_limit=args.line_limit,
        token=args.token
    )

    if full_context.startswith("Error:"):
        print(full_context)
        return

    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(full_context, encoding="utf-8")
            print(f"✅ Context successfully written to {output_path.resolve()}")
        except IOError as e:
            print(f"Error: Could not write to file {args.output}. Details: {e}")
    else:
        # If no output file, just print the context to the console.
        print("\n" + "="*80)
        print("LLM CONTEXT SNAPSHOT")
        print("="*80 + "\n")
        print(full_context)

if __name__ == "__main__":
    main()