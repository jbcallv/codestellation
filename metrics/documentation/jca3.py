import re
import json
import random
import textstat
import subprocess
import sys
import requests
from pathlib import Path
from numpy import dot
from numpy.linalg import norm

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import OPENAI_CONFIG

def count_root_level_classes(java_content):
    # remove comments
    content = re.sub(r'//.*?$', '', java_content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'"(?:[^"\\]|\\.)*"', '', content)
    
    # count opening braces at nesting level 0 after 'class' keyword
    classes = 0
    brace_depth = 0
    tokens = re.split(r'(\{|\}|\bclass\b)', content)
    found_class = False
    
    for token in tokens:
        if token == 'class':
            if brace_depth == 0:
                found_class = True
        elif token == '{':
            if found_class and brace_depth == 0:
                classes += 1
                found_class = False
            brace_depth += 1
        elif token == '}':
            brace_depth -= 1
    
    return classes

def extract_raw_class_comment(java_content):
    package_match = re.search(r'package\s+[\w.]+\s*;', java_content)
    if package_match:
        search_content = java_content[package_match.end():]
    else:
        search_content = java_content

    pattern = r'/\*\*(.*?)\*/\s*(?:(?:public|private|protected)\s+)?(?:(?:static|final|abstract)\s+)*class\s+'
    matches = list(re.finditer(pattern, search_content, re.DOTALL))

    if matches:
        match = matches[-1]
        return match.group(1)

    return None

def extract_class_comment(java_content):
    raw_comment = extract_raw_class_comment(java_content)
    
    if not raw_comment:
        return None

    # clean up the comment lines
    lines = [line.strip().lstrip('*').strip() for line in raw_comment.split('\n')]
    # remove empty lines and annotation lines
    lines = [line for line in lines if line and not line.startswith('@')]

    text = ' '.join(lines)

    return text if text else None

def clean_javadoc_text(text):
    # inline tag removal
    text = re.sub(r'\{@\w+\s+[^}]*\}', '', text)

    # html tag removal
    text = re.sub(r'<[^>]+>', '', text)

    # whitespace removal
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def calculate_readability_metrics(text):
    if not text or len(text.split()) < 3:
        return None

    cleaned_text = clean_javadoc_text(text)

    if not cleaned_text or len(cleaned_text.split()) < 3:
        return None

    return {
        'flesch_reading_ease': round(textstat.flesch_reading_ease(cleaned_text), 2),
        'flesch_kincaid_grade': round(textstat.flesch_kincaid_grade(cleaned_text), 2),
        'gunning_fog': round(textstat.gunning_fog(cleaned_text), 2),
        'smog_index': round(textstat.smog_index(cleaned_text), 2),
        'automated_readability_index': round(textstat.automated_readability_index(cleaned_text), 2),
        'coleman_liau_index': round(textstat.coleman_liau_index(cleaned_text), 2),
        'word_count': len(cleaned_text.split())
    }

def get_embedding(text):
    headers = {
        'Authorization': f'Bearer {OPENAI_CONFIG["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'input': text,
        'model': 'text-embedding-3-large'
    }
    
    response = requests.post(
        'https://api.openai.com/v1/embeddings',
        headers=headers,
        json=data,
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()['data'][0]['embedding']

def cosine_similarity(vec1, vec2):
    return dot(vec1, vec2) / (norm(vec1) * norm(vec2))

def calculate_embedding_alignment(comment, code):
    try:
        comment_embedding = get_embedding(comment)
        code_embedding = get_embedding(code)
        similarity = cosine_similarity(comment_embedding, code_embedding)
        return round(float(similarity), 4)
    except:
        return None

def get_comment_line_range(file_path, content):
    package_match = re.search(r'package\s+[\w.]+\s*;', content)

    if package_match:
        search_content = content[package_match.end():]
        offset = package_match.end()
    else:
        search_content = content
        offset = 0

    pattern = r'/\*\*(.*?)\*/\s*(?:(?:public|private|protected)\s+)?(?:(?:static|final|abstract)\s+)*class\s+'

    matches = list(re.finditer(pattern, search_content, re.DOTALL))

    if not matches:
        return None

    match = matches[-1]

    # find where the comment actually ends (*/)
    comment_pattern = r'/\*\*(.*?)\*/'
    comment_match = re.search(comment_pattern, match.group(0), re.DOTALL)

    if not comment_match:
        return None

    actual_start = offset + match.start()
    actual_comment_end = offset + match.start() + comment_match.end()

    comment_start = content[:actual_start].count('\n') + 1
    comment_end = content[:actual_comment_end].count('\n') + 1

    return (comment_start, comment_end)

def get_git_remote_url(repo_dir):
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        url = result.stdout.strip()
        
        # convert git@github.com:user/repo.git to https://github.com/user/repo
        if url.startswith('git@'):
            url = re.sub(r'^git@([^:]+):', r'https://\1/', url)
        
        # remove .git suffix
        url = re.sub(r'\.git$', '', url)
        
        return url
    except:
        return None

def build_commit_url(repo_url, commit_hash):
    if not repo_url:
        return None
    
    # github/gitlab pattern
    if 'github.com' in repo_url or 'gitlab.com' in repo_url:
        return f"{repo_url}/commit/{commit_hash}"
    
    # bitbucket pattern
    if 'bitbucket.org' in repo_url:
        return f"{repo_url}/commits/{commit_hash}"
    
    return None

def is_substantive_comment_change(repo_dir, commit_hash, relative_path, line_range):
    start_line, end_line = line_range

    try:
        # get full diff ignoring whitespace (-w) parts
        result = subprocess.run(
            ['git', 'show', f'{commit_hash}', '-w', '--', str(relative_path)],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return False

        diff_output = result.stdout

        # check if this is initial file creation
        if '--- /dev/null' in diff_output:
            return False

        # parse diff hunks to see if any overlap with our line range
        for line in diff_output.split('\n'):
            if line.startswith('@@'):
                # extract line numbers from hunk header: @@ -start,count +start,count @@
                match = re.search(r'@@ -(\d+),?\d* \+(\d+),?\d* @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    old_end = old_start + old_count - 1

                    # check if hunk overlaps with comment range [start_line, end_line]
                    if old_start <= end_line and old_end >= start_line:
                        return True

        return False
    except:
        return False

def get_git_comment_history(file_path, repo_dir, line_range):
    if not line_range:
        return None

    start_line, end_line = line_range
    relative_path = Path(file_path).relative_to(repo_dir)

    try:
        # get total commits for the entire file
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD', '--', str(relative_path)],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        total_commits = int(result.stdout.strip()) if result.stdout.strip() else 0

        # get commits that modified the comment lines
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-L{start_line},{end_line}:{relative_path}'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # extract commit hashes
        all_commit_hashes = []
        if result.stdout.strip():
            for line in result.stdout.split('\n'):
                match = re.match(r'^([0-9a-f]+)\s', line)
                if match:
                    all_commit_hashes.append(match.group(1))
        
        # filter for substantive changes only
        substantive_commit_hashes = []
        for commit_hash in all_commit_hashes:
            if is_substantive_comment_change(repo_dir, commit_hash, relative_path, line_range):
                substantive_commit_hashes.append(commit_hash)
        
        comment_commits = len(substantive_commit_hashes)

        # get last modification date for the comment
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ci', f'-L{start_line},{end_line}:{relative_path}'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        last_modified = result.stdout.strip().split('\n')[0] if result.stdout.strip() else None

        modification_ratio = round(comment_commits / total_commits, 4) if total_commits > 0 else 0

        # build commit URLs
        repo_url = get_git_remote_url(repo_dir)
        commit_urls = []
        if repo_url:
            for commit_hash in substantive_commit_hashes:
                url = build_commit_url(repo_url, commit_hash)
                if url:
                    commit_urls.append(url)

        return {
            'total_file_commits': total_commits,
            'comment_commits': comment_commits,
            'modification_ratio': modification_ratio,
            'last_modified': last_modified,
            'commit_urls': commit_urls
        }
    except:
        return None

def find_java_files(repo_dir):
    repo_path = Path(repo_dir)
    java_files = []
    
    for java_file in repo_path.rglob('*.java'):
        file_str = str(java_file).lower()
        if any(x in file_str for x in ['test', 'interface', '/tests/', '/test/']):
            continue
        
        try:
            with open(java_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if re.search(r'\bclass\s+\w+', content):
                    # exclude files with more than one root-level class
                    if count_root_level_classes(content) == 1:
                        java_files.append(java_file)
        except:
            continue
    
    return java_files

def calculate_coverage_ratio(repo_dir):
    java_files = find_java_files(repo_dir)
    total_files = len(java_files)
    
    files_with_comments = 0
    for file_path in java_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if extract_class_comment(content):
                    files_with_comments += 1
        except:
            continue
    
    ratio = round(files_with_comments / total_files, 4) if total_files > 0 else 0
    
    return {
        'total_class_files': total_files,
        'files_with_comments': files_with_comments,
        'coverage_ratio': ratio
    }

def process_file(file_path, repo_dir):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return None
    
    raw_comment = extract_raw_class_comment(content)
    if not raw_comment:
        return None
    
    cleaned_comment = extract_class_comment(content)
    if not cleaned_comment:
        return None
    
    metrics = calculate_readability_metrics(cleaned_comment)
    if not metrics:
        return None
    
    relative_path = Path(file_path).relative_to(repo_dir)
    
    # embedding alignment
    embedding_alignment = calculate_embedding_alignment(cleaned_comment, content)
    if embedding_alignment:
        metrics['embedding_alignment'] = embedding_alignment
    
    # git history
    line_range = get_comment_line_range(file_path, content)
    git_history = get_git_comment_history(file_path, repo_dir, line_range)
    if git_history:
        metrics['git_history'] = git_history
    
    return {
        'file_path': str(relative_path),
        'comment': cleaned_comment,
        'raw_comment': raw_comment,
        'full_code': content,
        'metrics': metrics
    }

def main(repo_dir, output_file, num_samples):
    # calculate coverage ratio first
    coverage = calculate_coverage_ratio(repo_dir)
    print(f"Coverage ratio: {coverage['coverage_ratio']} ({coverage['files_with_comments']}/{coverage['total_class_files']})")
    
    java_files = find_java_files(repo_dir)
    print(f"Found {len(java_files)} valid Java class files")
    
    results = []
    sampled_count = 0
    
    if num_samples and num_samples < len(java_files):
        random.shuffle(java_files)
        print(f"Sampling up to {num_samples} files with valid comments")
    
    for file_path in java_files:
        if num_samples and sampled_count >= num_samples:
            break
            
        result = process_file(file_path, repo_dir)
        if result:
            results.append(result)
            sampled_count += 1
            print(f"Processed ({sampled_count}): {result['file_path']}")
    
    output = {
        'coverage': coverage,
        'files': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nProcessed {len(results)} files. Output saved to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python java_comment_analyzer.py <repo_dir> <output_file> <num_samples>")
        print("Example: python java_comment_analyzer.py ./my-repo output.json 50")
        print("         python java_comment_analyzer.py ./my-repo output.json all")
        sys.exit(1)
    
    repo_dir = sys.argv[1]
    output_file = sys.argv[2]
    num_samples = int(sys.argv[3]) if sys.argv[3] != 'all' else None
    
    main(repo_dir, output_file, num_samples)
