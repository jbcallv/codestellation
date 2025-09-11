import os
import json
import sys
import statistics
import glob

sys.path.append("../../")
from openai_client import judge_file_summary_openai
from llm_client import summarize_file_single_llm


def find_project_files(project_name):
    # go up two directories and look for results
    results_dir = os.path.join('..', '..', 'results')
    
    if not os.path.exists(results_dir):
        print(f"results directory not found: {results_dir}")
        return None, None
    
    # look for project directory
    project_dir = os.path.join(results_dir, project_name)
    if not os.path.exists(project_dir):
        print(f"project directory not found: {project_dir}")
        return None, None
    
    # find eval and summary files
    eval_files = glob.glob(os.path.join(project_dir, '*eval*.json'))
    summary_files = glob.glob(os.path.join(project_dir, f'summary_{project_name}.json'))
    
    if not eval_files:
        print(f"no eval files found in {project_dir}")
        return None, None
    
    if not summary_files:
        print(f"no summary file found: summary_{project_name}.json")
        return None, None
    
    return eval_files[0], summary_files[0]


def load_top_n_samples(eval_file, n):
    with open(eval_file, 'r') as f:
        data = json.load(f)
    
    individual_results = data.get('individual_results', [])
    top_n = individual_results[:n]
    
    file_paths = []
    for result in top_n:
        if 'file_path' in result:
            file_paths.append(result['file_path'])
    
    return file_paths


def load_codestellation_summaries(summary_file):
    with open(summary_file, 'r') as f:
        data = json.load(f)
    
    return data.get('file_summaries', {})


def read_file_content(file_path):
    actual_path = os.path.join('..', '..', file_path)
    
    try:
        with open(actual_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"error reading {file_path}: {e}")
        return None


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


def run_ablation_study(project_name, n_samples, output_file):
    # find project files
    eval_file, summary_file = find_project_files(project_name)
    if not eval_file or not summary_file:
        return
    
    print(f"found eval file: {eval_file}")
    print(f"found summary file: {summary_file}")
    
    # load data
    file_paths = load_top_n_samples(eval_file, n_samples)
    codestellation_summaries = load_codestellation_summaries(summary_file)
    
    print(f"processing {len(file_paths)} files")
    
    baseline_results = []
    codestellation_results = []
    baseline_scores = []
    codestellation_scores = []
    
    for i, file_path in enumerate(file_paths):
        print(f"processing file {i+1}/{len(file_paths)}: {file_path}")
        
        # read file content
        file_content = read_file_content(file_path)
        if file_content is None:
            continue
        
        # check if codestellation summary exists
        if file_path not in codestellation_summaries:
            print(f"  warning: no codestellation summary for {file_path}")
            continue
        
        codestellation_summary = codestellation_summaries[file_path]
        
        # generate baseline summary
        print("  generating baseline summary...")
        baseline_summary = summarize_file_single_llm(file_content, file_path)
        
        # judge baseline summary
        print("  judging baseline summary...")
        baseline_judgment = judge_file_summary_openai(file_content, baseline_summary)
        baseline_results.append({
            'file_path': file_path,
            'summary': baseline_summary,
            'scores': baseline_judgment['scores'],
            'raw_response': baseline_judgment['raw_response']
        })
        baseline_scores.append(baseline_judgment['scores'])
        
        # judge codestellation summary
        print("  judging codestellation summary...")
        codestellation_judgment = judge_file_summary_openai(file_content, codestellation_summary)
        codestellation_results.append({
            'file_path': file_path,
            'summary': codestellation_summary,
            'scores': codestellation_judgment['scores'],
            'raw_response': codestellation_judgment['raw_response']
        })
        codestellation_scores.append(codestellation_judgment['scores'])
    
    # compute statistics
    baseline_stats = compute_statistics(baseline_scores)
    codestellation_stats = compute_statistics(codestellation_scores)
    
    # compute improvements
    improvements = compute_improvements(baseline_scores, codestellation_scores)
    
    # save results
    results = {
        'project_name': project_name,
        'n_samples': n_samples,
        'total_processed': len(baseline_results),
        'baseline_evaluation': {
            'statistics': baseline_stats,
            'individual_results': baseline_results
        },
        'codestellation_evaluation': {
            'statistics': codestellation_stats,
            'individual_results': codestellation_results
        },
        'comparison': improvements,
        'source_files': {
            'eval_file': eval_file,
            'summary_file': summary_file
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print_summary(results)
    print(f"results saved to: {output_file}")


def compute_improvements(baseline_scores, codestellation_scores):
    criteria = ["content_adequacy", "conciseness", "fluency_understandability"]
    improvements = {}
    
    for criterion in criteria:
        baseline_values = [s[criterion] for s in baseline_scores if s.get(criterion) is not None]
        codestellation_values = [s[criterion] for s in codestellation_scores if s.get(criterion) is not None]
        
        if baseline_values and codestellation_values:
            baseline_mean = statistics.mean(baseline_values)
            codestellation_mean = statistics.mean(codestellation_values)
            
            # count improvements at file level
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


def print_summary(results):
    print("\n" + "="*60)
    print("ABLATION STUDY RESULTS")
    print("="*60)
    print(f"project: {results['project_name']}")
    print(f"samples: {results['total_processed']}/{results['n_samples']}")
    
    print("\nScore Comparisons (Codestellation vs Baseline):")
    for criterion, data in results['comparison'].items():
        print(f"  {criterion}:")
        print(f"    Baseline: {data['baseline_mean']:.3f}")
        print(f"    Codestellation: {data['codestellation_mean']:.3f}")
        print(f"    Improvement: {data['mean_improvement']:+.3f} ({data['percent_improvement']:+.1f}%)")
        print(f"    Files improved: {data['files_improved']}/{results['total_processed']} ({data['improvement_rate']:.1%})")


def main():
    if len(sys.argv) != 4:
        print("usage: python run_ablation_study.py <project_name> <n_samples> <output_file>")
        print("example: python run_ablation_study.py mongo 20 ablation_results.json")
        return
    
    project_name = sys.argv[1]
    n_samples = int(sys.argv[2])
    output_file = sys.argv[3]
    
    run_ablation_study(project_name, n_samples, output_file)


if __name__ == "__main__":
    main()
