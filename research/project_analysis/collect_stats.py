import os
import sys
import json
import re
import subprocess


def find_java_files(project_dir):
    java_files = []
    for root, dirs, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                if not is_excluded_file(file_path):
                    java_files.append(file_path)
    return java_files


def is_excluded_file(file_path):
    lowercase_path = file_path.lower()

    exclude_patterns = ['test', 'tests']

    return any(pattern in lowercase_path for pattern in exclude_patterns)


def extract_file_level_comment(file_content):
    lines = file_content.split('\n')
    in_comment = False
    comment_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('/**'):
            in_comment = True
            comment_lines.append(stripped)
            continue
        
        if in_comment and stripped.endswith('*/'):
            comment_lines.append(stripped)
            comment_text = clean_javadoc(comment_lines)
            
            if not is_license_comment(comment_text):
                return comment_text
            
            in_comment = False
            comment_lines = []
            continue
        
        if in_comment:
            comment_lines.append(stripped)
    
    return None


def clean_javadoc(comment_lines):
    cleaned_lines = []
    
    for line in comment_lines:
        line = line.replace('/**', '').replace('*/', '')
        line = re.sub(r'^\s*\*\s?', '', line)
        if line.strip() and not line.strip().startswith('@'):
            cleaned_lines.append(line.strip())
    
    return ' '.join(cleaned_lines)


def is_license_comment(comment_text):
    license_keywords = ['copyright', 'license', 'licensed', 'apache', 'permission']
    comment_lower = comment_text.lower()
    return any(keyword in comment_lower for keyword in license_keywords)


def count_lines_of_code(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # count non-empty, non-comment lines
        code_lines = 0
        in_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            if stripped.startswith('/*') or stripped.startswith('/**'):
                in_comment = True
                continue
            
            if in_comment and '*/' in stripped:
                in_comment = False
                continue
            
            if in_comment or stripped.startswith('//'):
                continue
            
            code_lines += 1
        
        return code_lines
    except:
        return 0


def get_git_stats(project_dir):
    try:
        # total commits
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                              cwd=project_dir, capture_output=True, text=True)
        total_commits = int(result.stdout.strip()) if result.returncode == 0 else 0
        
        # number of contributors
        result = subprocess.run(['git', 'shortlog', '-sn'], 
                              cwd=project_dir, capture_output=True, text=True)
        contributors = len(result.stdout.strip().split('\n')) if result.returncode == 0 else 0
        
        return total_commits, contributors
    except:
        return 0, 0


def get_file_churn(project_dir, file_path):
    try:
        rel_path = os.path.relpath(file_path, project_dir)
        result = subprocess.run(['git', 'log', '--oneline', rel_path], 
                              cwd=project_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        return 0
    except:
        return 0


def analyze_documentation(java_files):
    documented_files = 0
    total_doc_length = 0
    doc_lengths = []
    
    for file_path in java_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = extract_file_level_comment(content)
            if doc:
                documented_files += 1
                doc_length = len(doc.split())
                total_doc_length += doc_length
                doc_lengths.append(doc_length)
        except:
            continue
    
    return {
        'documented_files': documented_files,
        'total_files': len(java_files),
        'documentation_coverage': documented_files / len(java_files) if java_files else 0,
        'avg_doc_length': total_doc_length / documented_files if documented_files > 0 else 0,
        'doc_lengths': doc_lengths
    }


def analyze_code_complexity(java_files):
    total_loc = 0
    file_locs = []
    
    for file_path in java_files:
        loc = count_lines_of_code(file_path)
        total_loc += loc
        file_locs.append(loc)
    
    return {
        'total_loc': total_loc,
        'avg_loc_per_file': total_loc / len(java_files) if java_files else 0,
        'file_locs': file_locs
    }


def analyze_maintenance(project_dir, java_files):
    total_commits, contributors = get_git_stats(project_dir)
    
    file_churns = []
    for file_path in java_files:
        churn = get_file_churn(project_dir, file_path)
        file_churns.append(churn)
    
    return {
        'total_commits': total_commits,
        'contributors': contributors,
        'avg_file_churn': sum(file_churns) / len(file_churns) if file_churns else 0,
        'file_churns': file_churns
    }


def collect_project_stats(project_dir):
    project_name = os.path.basename(os.path.abspath(project_dir))
    java_files = find_java_files(project_dir)
    
    print(f"analyzing {project_name} with {len(java_files)} java files")
    
    documentation_stats = analyze_documentation(java_files)
    complexity_stats = analyze_code_complexity(java_files)
    maintenance_stats = analyze_maintenance(project_dir, java_files)
    
    return {
        'project_name': project_name,
        'project_path': project_dir,
        'total_java_files': len(java_files),
        'documentation': documentation_stats,
        'complexity': complexity_stats,
        'maintenance': maintenance_stats
    }


def main():
    if len(sys.argv) != 3:
        print("usage: python collect_stats.py <project_dir> <output_file>")
        print("example: python collect_stats.py /path/to/project project_stats.json")
        return
    
    project_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(project_dir):
        print(f"directory {project_dir} does not exist")
        return
    
    stats = collect_project_stats(project_dir)
    
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"stats saved to {output_file}")
    print(f"documentation coverage: {stats['documentation']['documentation_coverage']:.2%}")
    print(f"average loc per file: {stats['complexity']['avg_loc_per_file']:.1f}")
    print(f"total commits: {stats['maintenance']['total_commits']}")


if __name__ == "__main__":
    main()
