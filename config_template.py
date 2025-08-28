### RENAME THIS FILE TO "config.py" AND POPULATE ALL VARIABLES

CLAUDE_CONFIG = {
    "model": "claude-3-5-haiku-20241022",
    "api_key": "<your api key>",
    "max_tokens": 4000,
    "temperature": 0
}

CHUNKING_CONFIG = {
    "window_size": 500,
    "overlap_size": 50,
    "min_chunk_size": 10,
    "respect_boundaries": True
}

PROJECT_CONFIG = {
    "supported_extensions": [".java"],
    "exclude_patterns": ["**/target/**", "**/build/**", "**/.git/**"],
    "include_test_files": False
}

SUMMARIZER_CONFIG = {
    "max_workers": 10,
    "max_dependency_context": 10
}