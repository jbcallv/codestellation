import os
import time
import json
import requests
import random
import threading

from config import CLAUDE_CONFIG
from stats_collector import stats


class PromptTracker:
    def __init__(self):
        self.filename = "prompt_logs/prompts.jsonl"
        self.lock = threading.Lock()

    def should_log(self):
        return random.randint(1, 100) <= 80 # log 80% of prompts

    def log_prompt(self, prompt_type, messages, response):
        try:
            if not self.should_log():
                return

            entry = {
                "prompt_type": prompt_type,
                "messages": messages,
                "response": response
            }

            with self.lock:
                os.makedirs("prompt_logs", exist_ok=True)
                with open(self.filename, 'a') as f:
                    f.write(json.dumps(entry) + '\n')

        except Exception as e:
            print("Something is wrong.", e)


prompt_tracker = PromptTracker()


def call_claude_with_backoff(messages, max_retries=10, api_key=CLAUDE_CONFIG["api_key"]):
    """Simple exponential backoff for Claude API calls"""
    for attempt in range(max_retries):
        try:
            stats.log_llm_call("api_request")

            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": CLAUDE_CONFIG["model"],
                "max_tokens": CLAUDE_CONFIG["max_tokens"],
                "temperature": CLAUDE_CONFIG["temperature"],
                "messages": messages
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            elif response.status_code == 429:
                wait_time = (2 ** attempt) + (time.time() % 1)
                print(f"Rate limited, waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                continue
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return f"Error: Failed to get response after {max_retries} attempts: {str(e)}"
            
            wait_time = (2 ** attempt) + (time.time() % 1)
            print(f"Request failed (attempt {attempt + 1}), retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    return "Error: Max retries exceeded"


def summarize_chunk(chunk_content, context=""):
    context_section = ""
    if context.strip():
        context_section = f"\n\nDependency Context:\n{context}"
    
    prompt = f"""Analyze this Java code chunk with full understanding of its dependencies.

Code Chunk:
```java
{chunk_content}
```

Dependency Context:
{context}

Using the dependency context above, create a comprehensive summary that explains:
1. What this code does and why (given the dependency behaviors)
2. How it integrates with the dependencies shown in context
3. The complete data flow and method interactions
4. Any patterns or logic that emerge from the dependency relationships

Write a detailed technical explanation that demonstrates deep understanding of how this code fits into the larger system."""

    messages = [{"role": "user", "content": prompt}]
    stats.log_llm_call("chunk_summary")
    return call_claude_with_backoff(messages)


def summarize_method(method_content, file_path, method_name):
    prompt = f"""Summarize this Java method for dependency analysis.

Method: {method_name} in {file_path}

```java
{method_content}
```

Provide a concise technical summary covering:
- Core functionality and purpose
- Key parameters and return behavior
- Side effects or state changes

Keep to 1-2 precise sentences for use as dependency context."""

    messages = [{"role": "user", "content": prompt}]
    stats.log_llm_call("method_summary")
    return call_claude_with_backoff(messages)


def summarize_file(chunk_summaries, file_path):
    chunks_text = "\n\n".join([f"Chunk {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])
    
    prompt = f"""Write a 3-4 sentence technical summary of this file's functionality.

File: {file_path}

Code Section Summaries:
{chunks_text}

Focus ONLY on what the code actually does:
1. What is the primary purpose of this file?
2. What are the key methods and what do they do?
3. What data does it manage and how?

Do NOT:
- Infer design patterns unless explicitly implemented (e.g., don't say "Repository Pattern" unless you see an interface)
- Describe architectural decisions that aren't evident in the code
- Make recommendations for future improvements
- Discuss scalability, complexity ratings, or maintainability
- Speculate about "potential integrations" or "system roles"

Be specific. Be direct. Describe only what you can see in the code."""

    messages = [{"role": "user", "content": prompt}]
    stats.log_llm_call("file_summary")

    response = call_claude_with_backoff(messages)
    prompt_tracker.log_prompt("file_summary", messages, response)
    return response #call_claude_with_backoff(messages)


def summarize_file_single_llm(file_content, file_path):
    prompt = f"""Create a comprehensive file-level summary from this Java file.

File: {file_path}

```java
{file_content}
```

Generate a complete technical summary that includes:
1. File's primary purpose and responsibility within the system
2. Main classes and their specific roles
3. Key public methods and their functionality
4. Important data structures and algorithms
5. Dependencies and how this file integrates with other components
6. Design patterns or architectural decisions

Structure as clear, informative paragraphs that fully document the file's implementation and purpose."""

    messages = [{"role": "user", "content": prompt}]
    return call_claude_with_backoff(messages)


def summarize_project(file_summaries, project_path):
    """Create project-level summary from file summaries"""
    files_text = "\n\n".join([f"File: {i+1}\n{summary}" for i, summary in enumerate(file_summaries)])
    
    prompt = f"""Create a high-level project summary from these file summaries.

Project: {project_path}
Total Files: {len(file_summaries)}

File Summaries:
{files_text}

Provide a project summary that includes:
- Overall project purpose and domain
- Main components and their interactions  
- Key architectural patterns
- Primary functionality and features
- Notable design decisions

Focus on the big picture and overall system architecture."""

    messages = [{"role": "user", "content": prompt}]
    stats.log_llm_call("project_summary")
    return call_claude_with_backoff(messages)
