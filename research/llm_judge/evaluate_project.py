import sys
import json
import random
import os
import statistics
from llm_judge import judge_file_summary, extract_scores


def load_project_data(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)


def sample_files(file_summaries, sample_size):
    file_paths = list(file_summaries.keys())
    
    if sample_size > len(file_paths):
        sample_size = len(file_paths)
        print(f"sample size reduced to {sample_size} (total available files)")
    
    return random.sample(file_paths, sample_size)


def read_file_content(file_path):
    actual_path = os.path.join('..', '..', file_path)

    try:
        with open(actual_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"error reading {file_path}: {e}")
        return None


def evaluate_summaries(sampled_paths, file_summaries):
    results = []
    all_scores = []
    
    for i, file_path in enumerate(sampled_paths):
        print(f"evaluating file {i+1}/{len(sampled_paths)}: {file_path}")
        
        file_content = read_file_content(file_path)
        if file_content is None:
            continue
            
        summary = file_summaries[file_path]
        judgment = judge_file_summary(file_content, summary)
        
        scores = judgment['scores']
        all_scores.append(scores)
        
        results.append({
            'file_path': file_path,
            'scores': scores,
            'raw_response': judgment['raw_response']
        })
    
    return results, all_scores


def compute_statistics(scores_list):
    if not scores_list:
        return {}
    
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


def save_results(results, statistics_data, output_path, sample_size):
    output_data = {
        'sample_size': sample_size,
        'total_evaluated': len(results),
        'statistics': statistics_data,
        'individual_results': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)


def print_summary(statistics_data, sample_size, total_evaluated):
    print(f"\nevaluation complete!")
    print(f"sample size: {sample_size}")
    print(f"files evaluated: {total_evaluated}")
    print("\naverage scores:")
    
    for criterion, stats in statistics_data.items():
        print(f"  {criterion}: {stats['mean']:.2f} (±{stats['stdev']:.2f})")


def main():
    if len(sys.argv) != 4:
        print("usage: python evaluate_project.py <json_file> <sample_size> <output_file>")
        print("example: python evaluate_project.py results/summary_guava.json 20 guava_eval.json")
        return
    
    json_path = sys.argv[1]
    sample_size = int(sys.argv[2])
    output_path = sys.argv[3]
    
    # load, process, and sample data
    project_data = load_project_data(json_path)
    file_summaries = project_data['file_summaries']
    
    sampled_paths = sample_files(file_summaries, sample_size)
    results, all_scores = evaluate_summaries(sampled_paths, file_summaries)
    
    statistics_data = compute_statistics(all_scores)
    
    save_results(results, statistics_data, output_path, sample_size)
    print_summary(statistics_data, sample_size, len(results))
    
    print(f"\ndetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
