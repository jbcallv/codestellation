import json
import random
import re
import os
import sys
sys.path.append('../..')
from llm_client import call_claude_with_backoff


def judge_file_summary(file_content, summary, language="Java"):
    prompt = f"""You will be provided with a {language} file ("File") and a textual summary of it ("Summary"). The goal of the Summary is to document the functionality implemented in the File. Your role is to evaluate the Summary across three criteria, providing as output for each of them a rating and a rationale.

# Evaluation Criteria
* Content adequacy: the extent to which the summary captures all important information that can be inferred from the source code.
* Conciseness: the extent to which the summary contains unnecessary information.
* Fluency & Understandability: the extent to which the summary is easy to read and understand.

For each criterion, provide a score on a scale from 1 to 5: 1 (Very poor), 2 (Poor), 3 (Fair), 4 (Good), 5 (Very good).

# File: {file_content}
# Summary: {summary}"""

    messages = [{"role": "user", "content": prompt}]
    response = call_claude_with_backoff(messages)
    
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

    # find all X/Y patterns in the response
    score_matches = re.findall(r'(\d)/(\d)', response)

    # simple approach - assign first 3 scores found to the 3 criteria in order
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]

    for i, match in enumerate(score_matches[:3]):
        if i < len(criteria):
            scores[criteria[i]] = int(match[0])  # take the X from X/Y

    return scores


def extract_file_level_comment(file_content):
    lines = file_content.split('\n')
    in_comment = False
    comment_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # start of javadoc comment
        if stripped.startswith('/**'):
            in_comment = True
            comment_lines.append(stripped)
            continue
        
        # end of javadoc comment
        if in_comment and stripped.endswith('*/'):
            comment_lines.append(stripped)
            comment_text = clean_javadoc(comment_lines)
            
            # skip license comments
            if not is_license_comment(comment_text):
                print(f"found comment: {comment_text[:100]}...")
                return comment_text
            
            # reset for next comment
            in_comment = False
            comment_lines = []
            continue
        
        # inside comment
        if in_comment:
            comment_lines.append(stripped)
    
    print("no non-license comment found")
    return None


def is_license_comment(comment_text):
    license_keywords = ['copyright', 'license', 'licensed', 'apache', 'permission']
    comment_lower = comment_text.lower()
    return any(keyword in comment_lower for keyword in license_keywords)


def clean_javadoc(comment_lines):
    cleaned_lines = []
    
    for line in comment_lines:
        # remove /** and */
        line = line.replace('/**', '').replace('*/', '')
        # remove leading * and whitespace
        line = re.sub(r'^\s*\*\s?', '', line)
        # skip empty lines and tags
        if line.strip() and not line.strip().startswith('@'):
            cleaned_lines.append(line.strip())
    
    return ' '.join(cleaned_lines)


def sample_and_judge(codestellation_file, sample_size, output_file):
    with open(codestellation_file, 'r') as f:
        data = json.load(f)
    
    file_summaries = data['file_summaries']
    file_paths = list(file_summaries.keys())
    
    if sample_size > len(file_paths):
        sample_size = len(file_paths)
        print(f"sample size reduced to {sample_size} (total available files)")
    
    sampled_paths = random.sample(file_paths, sample_size)
    
    results = []
    human_scores = []
    ai_scores = []
    
    for i, file_path in enumerate(sampled_paths):
        print(f"processing file {i+1}/{len(sampled_paths)}: {file_path}")
        
        # adjust path for running from research/ directory
        actual_path = os.path.join('..', '..', file_path)
        
        try:
            with open(actual_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # extract human documentation
            human_doc = extract_file_level_comment(file_content)
            ai_summary = file_summaries[file_path]
            
            file_result = {
                'file_path': file_path,
                'human_doc': human_doc,
                'ai_summary': ai_summary,
                'human_judgment': None,
                'ai_judgment': None
            }
            
            # judge human documentation if it exists
            if human_doc:
                human_judgment = judge_file_summary(file_content, human_doc)
                file_result['human_judgment'] = human_judgment
                human_scores.append(human_judgment['scores'])
            else:
                file_result['human_doc_missing'] = True
            
            # judge ai summary
            ai_judgment = judge_file_summary(file_content, ai_summary)
            file_result['ai_judgment'] = ai_judgment
            ai_scores.append(ai_judgment['scores'])
            
            results.append(file_result)
            
        except Exception as e:
            print(f"error processing {file_path}: {e}")
            results.append({
                'file_path': file_path,
                'error': str(e)
            })
    
    # calculate averages
    human_avg = calculate_averages(human_scores)
    ai_avg = calculate_averages(ai_scores)
    
    final_result = {
        'sample_size': sample_size,
        'files_with_human_docs': len(human_scores),
        'human_averages': human_avg,
        'ai_averages': ai_avg,
        'individual_results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"results saved to {output_file}")
    print(f"human docs found: {len(human_scores)}/{sample_size}")
    print(f"human averages: {human_avg}")
    print(f"ai averages: {ai_avg}")
    
    return final_result


def calculate_averages(scores_list):
    if not scores_list:
        return {"content_adequacy": 0, "conciseness": 0, "fluency_understandability": 0}
    
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]
    averages = {}
    
    for criterion in criteria:
        valid_scores = [s[criterion] for s in scores_list if s.get(criterion) is not None]
        averages[criterion] = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    
    return averages


def main():
    import sys
    
    if len(sys.argv) != 4:
        print("usage: python llm_judge.py <codestellation_file> <sample_size> <output_file>")
        print("example: python llm_judge.py ../summary_guava.json 50 guava_comparison.json")
        return
    
    codestellation_file = sys.argv[1]
    sample_size = int(sys.argv[2])
    output_file = sys.argv[3]
    
    sample_and_judge(codestellation_file, sample_size, output_file)


if __name__ == "__main__":
    main()
