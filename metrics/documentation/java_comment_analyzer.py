import re
import json
import random
import textstat
from pathlib import Path

def extract_class_comment(java_content):
    pattern = r'/\*\*(.*?)\*/\s*(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:abstract)?\s*class'
    match = re.search(pattern, java_content, re.DOTALL)
    
    if match:
        comment_text = match.group(1)
        lines = [line.strip().lstrip('*').strip() for line in comment_text.split('\n')]
        lines = [line for line in lines if line and not line.startswith('@')]
        return ' '.join(lines)
    
    return None

def calculate_readability_metrics(text):
    if not text or len(text.split()) < 3:
        return None
    
    return {
        'flesch_reading_ease': round(textstat.flesch_reading_ease(text), 2),
        'flesch_kincaid_grade': round(textstat.flesch_kincaid_grade(text), 2),
        'gunning_fog': round(textstat.gunning_fog(text), 2),
        'smog_index': round(textstat.smog_index(text), 2),
        'automated_readability_index': round(textstat.automated_readability_index(text), 2),
        'coleman_liau_index': round(textstat.coleman_liau_index(text), 2),
        'word_count': len(text.split())
    }

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
                    java_files.append(java_file)
        except:
            continue
    
    return java_files

def process_file(file_path, repo_dir):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return None
    
    comment = extract_class_comment(content)
    if not comment:
        return None
    
    metrics = calculate_readability_metrics(comment)
    if not metrics:
        return None
    
    relative_path = Path(file_path).relative_to(repo_dir)
    
    return {
        'file_path': str(relative_path),
        'comment': comment,
        'full_code': content,
        'metrics': metrics
    }

def main(repo_dir, output_file, num_samples):
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
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nProcessed {len(results)} files. Output saved to {output_file}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python java_comment_analyzer.py <repo_dir> <output_file> <num_samples>")
        print("Example: python java_comment_analyzer.py ./my-repo output.json 50")
        print("         python java_comment_analyzer.py ./my-repo output.json all")
        sys.exit(1)
    
    repo_dir = sys.argv[1]
    output_file = sys.argv[2]
    num_samples = int(sys.argv[3]) if sys.argv[3] != 'all' else None
    
    main(repo_dir, output_file, num_samples)
