import time
import json
import requests
from config import CLAUDE_CONFIG


def call_claude_with_backoff(messages, max_retries=10):
    """Simple exponential backoff for Claude API calls"""
    for attempt in range(max_retries):
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": CLAUDE_CONFIG["api_key"],
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
    """Summarize a code chunk with optional dependency context"""
    context_section = ""
    if context.strip():
        context_section = f"\n\nDependency Context:\n{context}"
    
    prompt = f"""Analyze this Java code chunk and provide a concise summary.

Code Chunk:
```java
{chunk_content}
```{context_section}

Provide a summary that includes:
- Main purpose/functionality
- Key methods or logic
- Important variables or data structures
- Any notable patterns or algorithms

Keep the summary concise (2-4 sentences) but informative."""

    messages = [{"role": "user", "content": prompt}]
    return call_claude_with_backoff(messages)


def summarize_method(method_content, file_path, method_name):
    """Summarize a specific method for dependency context"""
    prompt = f"""Summarize this Java method for use as dependency context.

File: {file_path}
Method: {method_name}

```java
{method_content}
```

Provide a brief summary focusing on:
- What the method does
- Key parameters and return value
- Important behavior or side effects

Keep it concise (1-2 sentences) for use as context in other summaries."""

    messages = [{"role": "user", "content": prompt}]
    return call_claude_with_backoff(messages)


def summarize_file(chunk_summaries, file_path):
    """Create file-level summary from chunk summaries"""
    chunks_text = "\n\n".join([f"Chunk {i+1}: {summary}" for i, summary in enumerate(chunk_summaries)])
    
    prompt = f"""Create a comprehensive file-level summary from these chunk summaries.

File: {file_path}

Chunk Summaries:
{chunks_text}

Provide a file summary that includes:
- Overall purpose and responsibility of the file
- Main classes and their roles
- Key methods and functionality
- Dependencies and relationships
- Design patterns or architectural notes

Structure the summary clearly and keep it comprehensive but concise."""

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
    return call_claude_with_backoff(messages)