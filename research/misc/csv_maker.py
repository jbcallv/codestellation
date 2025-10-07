import json
import csv

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def load_jsonl(filepath):
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def extract_file_path_from_prompt(prompt_content):
    for line in prompt_content.split('\n'):
        if line.startswith('File: '):
            return line.replace('File: ', '').strip()
    return None

def build_prompt_map(prompts_data):
    prompt_map = {}
    for item in prompts_data:
        if 'messages' in item and len(item['messages']) > 0:
            content = item['messages'][0]['content']
            file_path = extract_file_path_from_prompt(content)
            if file_path:
                prompt_map[file_path] = content
    return prompt_map

def extract_rows(eval_data, prompt_map):
    rows = []
    
    cs_results = {r['file_path']: r for r in eval_data['codestellation_evaluation']['individual_results']}
    sa_results = {r['file_path']: r for r in eval_data['baseline_evaluation']['individual_results']}
    
    for file_path in cs_results.keys():
        if file_path not in sa_results or file_path not in prompt_map:
            continue
            
        cs_entry = cs_results[file_path]
        sa_entry = sa_results[file_path]

        print(cs_entry, sa_entry)
        
        row = {
            'cs_input': prompt_map[file_path],
            'cs_pred': cs_entry['summary'],
            'sa_pred': sa_entry['summary'],
            'cs_content_ad': cs_entry['scores']['content_adequacy'],
            'sa_content_ad': sa_entry['scores']['content_adequacy']
        }
        rows.append(row)
    
    return rows

def write_csv(rows, output_path):
    fieldnames = ['cs_input', 'cs_pred', 'sa_pred', 'cs_content_ad', 'sa_content_ad']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    eval_path = '../../results/hive/hive_ablation.json'
    prompts_path = '../../results/hive/prompts.jsonl'
    output_path = 'output.csv'
    
    eval_data = load_json(eval_path)
    prompts_data = load_jsonl(prompts_path)
    
    prompt_map = build_prompt_map(prompts_data)
    rows = extract_rows(eval_data, prompt_map)
    write_csv(rows, output_path)
    
    print(f'Wrote {len(rows)} rows to {output_path}')

if __name__ == '__main__':
    main()
