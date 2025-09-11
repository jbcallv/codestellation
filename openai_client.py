import time
import json
import requests

from config import OPENAI_CONFIG


def call_openai_with_backoff(messages, max_retries=10, api_key=OPENAI_CONFIG["api_key"]):
    for attempt in range(max_retries):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": OPENAI_CONFIG["model"],
                "max_completion_tokens": OPENAI_CONFIG["max_tokens"],
                "temperature": OPENAI_CONFIG["temperature"],
                "messages": messages
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                wait_time = (2 ** attempt) + (time.time() % 1)
                print(f"rate limited, waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                continue
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return f"error: failed to get response after {max_retries} attempts: {str(e)}"
            
            wait_time = (2 ** attempt) + (time.time() % 1)
            print(response.text)
            print(f"request failed (attempt {attempt + 1}), retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    return "error: max retries exceeded"


def summarize_file_single_llm(file_content, file_path):
    prompt = f"""Analyze this Java file and provide a comprehensive file-level summary.

File: {file_path}

```java
{file_content}
```

Provide a file summary that includes:
- Overall purpose and responsibility of the file
- Main classes and their roles
- Key methods and functionality
- Dependencies and relationships
- Design patterns or architectural notes

Structure the summary clearly and keep it comprehensive but concise."""

    messages = [{"role": "user", "content": prompt}]
    return call_openai_with_backoff(messages)


def judge_file_summary_openai(file_content, summary, language="Java"):
    prompt = f"""You will be provided with a {language} file ("File") and a textual summary of it ("Summary"). The goal of the Summary is to document the functionality implemented in the File. Your role is to evaluate the Summary across three criteria, providing as output for each of them a rating and a rationale.

# Evaluation Criteria
* Content adequacy: the extent to which the summary captures all important information that can be inferred from the source code.
* Conciseness: the extent to which the summary contains unnecessary information.
* Fluency & Understandability: the extent to which the summary is easy to read and understand.

For each criterion, provide a score on a scale from 1 to 5: 1 (Very poor), 2 (Poor), 3 (Fair), 4 (Good), 5 (Very good).

# File: {file_content}
# Summary: {summary}"""

    messages = [{"role": "user", "content": prompt}]
    response = call_openai_with_backoff(messages)
    scores = extract_scores(response)
    
    return {
        "scores": scores,
        "raw_response": response
    }


def extract_scores(response):
    import re

    scores = {
        "content_adequacy": None,
        "conciseness": None,
        "fluency_understandability": None
    }

    score_matches = re.findall(r'(\d)/(\d)', response)
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]

    for i, match in enumerate(score_matches[:3]):
        if i < len(criteria):
            scores[criteria[i]] = int(match[0])

    return scores
