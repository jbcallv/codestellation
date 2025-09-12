import json
import re
import sys


def extract_scores_fixed(response):
    scores = {"content_adequacy": None, "conciseness": None, "fluency_understandability": None}

    if not response:
        return scores

    # Try specific patterns first
    patterns = [
        r'\*\*Content adequacy:?\*?\*?\s*(\d+)',
        r'\*\*Conciseness:?\*?\*?\s*(\d+)',
        r'\*\*Fluency & Understandability:?\*?\*?\s*(\d+)'
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            score_keys = list(scores.keys())
            scores[score_keys[i]] = int(match.group(1))

    # If we have all scores, return
    if all(score is not None for score in scores.values()):
        return scores

    # Try fallback patterns
    fallbacks = [
        re.findall(r'(\d)/\d+', response),  # X/Y format
        re.findall(r'Score:\s*([1-5])', response, re.IGNORECASE),  # Score: X
        re.findall(r'\*\*[^*]+\*\*:\s*([1-5])', response)  # Generic **: X
    ]

    for matches in fallbacks:
        if len(matches) >= 3:
            for i, key in enumerate(scores.keys()):
                if scores[key] is None and i < len(matches):
                    scores[key] = int(matches[i])
            break

    return scores


def fix_json_scores(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    fixed_count = 0
    
    # fix baseline scores
    if 'baseline_evaluation' in data and 'individual_results' in data['baseline_evaluation']:
        for result in data['baseline_evaluation']['individual_results']:
            if result['scores'] and any(v is None for v in result['scores'].values()):
                new_scores = extract_scores_fixed(result['raw_response'])
                old_scores = result['scores'].copy()
                result['scores'].update(new_scores)
                
                if old_scores != result['scores']:
                    fixed_count += 1
    
    # fix codestellation scores
    if 'codestellation_evaluation' in data and 'individual_results' in data['codestellation_evaluation']:
        for result in data['codestellation_evaluation']['individual_results']:
            if result['scores'] and any(v is None for v in result['scores'].values()):
                new_scores = extract_scores_fixed(result['raw_response'])
                old_scores = result['scores'].copy()
                result['scores'].update(new_scores)
                
                if old_scores != result['scores']:
                    fixed_count += 1
    
    # recompute statistics
    if 'baseline_evaluation' in data:
        baseline_scores = [r['scores'] for r in data['baseline_evaluation']['individual_results']]
        data['baseline_evaluation']['statistics'] = compute_stats(baseline_scores)
    
    if 'codestellation_evaluation' in data:
        codestellation_scores = [r['scores'] for r in data['codestellation_evaluation']['individual_results']]
        data['codestellation_evaluation']['statistics'] = compute_stats(codestellation_scores)
    
    # recompute comparison if present
    if 'comparison' in data and 'baseline_evaluation' in data and 'codestellation_evaluation' in data:
        baseline_scores = [r['scores'] for r in data['baseline_evaluation']['individual_results']]
        codestellation_scores = [r['scores'] for r in data['codestellation_evaluation']['individual_results']]
        data['comparison'] = compute_improvements(baseline_scores, codestellation_scores)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"fixed {fixed_count} score entries")
    print(f"output saved to: {output_file}")


def compute_stats(scores_list):
    import statistics
    
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]
    stats = {}
    
    for criterion in criteria:
        valid_scores = [s[criterion] for s in scores_list if s.get(criterion) is not None]
        
        if valid_scores:
            stats[criterion] = {
                'mean': statistics.mean(valid_scores),
                'median': statistics.median(valid_scores),
                'stdev': statistics.stdev(valid_scores) if len(valid_scores) > 1 else 0,
                'min': min(valid_scores),
                'max': max(valid_scores),
                'count': len(valid_scores)
            }
        else:
            stats[criterion] = {'mean': 0, 'median': 0, 'stdev': 0, 'min': 0, 'max': 0, 'count': 0}
    
    return stats


def compute_improvements(baseline_scores, codestellation_scores):
    import statistics
    
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]
    improvements = {}
    
    for criterion in criteria:
        baseline_values = [s[criterion] for s in baseline_scores if s.get(criterion) is not None]
        codestellation_values = [s[criterion] for s in codestellation_scores if s.get(criterion) is not None]
        
        if baseline_values and codestellation_values:
            baseline_mean = statistics.mean(baseline_values)
            codestellation_mean = statistics.mean(codestellation_values)
            
            file_improvements = 0
            file_degradations = 0
            for i in range(min(len(baseline_scores), len(codestellation_scores))):
                b_score = baseline_scores[i].get(criterion)
                c_score = codestellation_scores[i].get(criterion)
                if b_score is not None and c_score is not None:
                    if c_score > b_score:
                        file_improvements += 1
                    elif c_score < b_score:
                        file_degradations += 1
            
            improvements[criterion] = {
                'baseline_mean': baseline_mean,
                'codestellation_mean': codestellation_mean,
                'mean_improvement': codestellation_mean - baseline_mean,
                'percent_improvement': ((codestellation_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0,
                'files_improved': file_improvements,
                'files_degraded': file_degradations,
                'improvement_rate': file_improvements / len(baseline_values) if baseline_values else 0
            }
    
    return improvements


def main():
    if len(sys.argv) != 3:
        print("usage: python fix_scores.py <input_json> <output_json>")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    fix_json_scores(input_file, output_file)


if __name__ == "__main__":
    main()
