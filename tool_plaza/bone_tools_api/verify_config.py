#!/usr/bin/env python3
"""Verify public tool API environment configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv


def _present(value: str | None, placeholder: str | None = None) -> bool:
    return bool(value) and value != placeholder


def verify_environment():
    """Check required environment files and API keys."""
    print("=" * 60)
    print("Tool API configuration check")
    print("=" * 60)

    env_file = Path(".env")
    env_example = Path(".env.example")
    openai_file = Path(".openai")

    print("\nConfiguration files:")
    print(f"  {'OK' if env_example.exists() else 'WARN'} .env.example: {'found' if env_example.exists() else 'not found'}")
    print(f"  {'OK' if env_file.exists() else 'WARN'} .env: {'found' if env_file.exists() else 'not found'}")
    print(f"  {'OK' if openai_file.exists() else 'INFO'} .openai: {'found' if openai_file.exists() else 'not found'}")

    if env_file.exists():
        load_dotenv(env_file)
        print("\nLoaded .env")
    elif openai_file.exists():
        load_dotenv(openai_file)
        print("\nLoaded .openai")
    else:
        print("\nERROR: no .env or .openai file found")
        return False

    print("\nEnvironment variables:")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base = os.getenv("OPENAI_API_BASE")
    semantic_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    print(f"  {'OK' if openai_key else 'ERROR'} OPENAI_API_KEY: {'configured' if openai_key else 'missing'}")
    print(f"  {'OK' if openai_base else 'INFO'} OPENAI_API_BASE: {openai_base if openai_base else 'default provider endpoint'}")
    print(
        f"  {'OK' if _present(semantic_key, 'your_semantic_scholar_api_key_here') else 'ERROR'} "
        f"SEMANTIC_SCHOLAR_API_KEY: {'configured' if _present(semantic_key, 'your_semantic_scholar_api_key_here') else 'missing'}"
    )

    print("\nSemantic Scholar tool:")
    try:
        from tools.semanticscholar import SemanticScholarSearchTool
        tool = SemanticScholarSearchTool()
        print("  OK SemanticScholarSearchTool initialized")
        print(f"  Tool name: {tool.name}")
        print(f"  API key: {'configured' if tool.api_key else 'missing'}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    print("\n" + "=" * 60)
    print("Configuration check passed")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = verify_environment()
    exit(0 if success else 1)
