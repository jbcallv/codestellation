import json
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#8E5572', '#6A994E', '#277DA1', '#F9844A', '#4D5382', '#90E0EF']

def load_all_projects(results_dir):
    projects = []
    for project_name in os.listdir(results_dir):
        project_path = os.path.join(results_dir, project_name)
        if not os.path.isdir(project_path) or project_name == 'guava':
            continue
            
        json_file = os.path.join(project_path, f"{project_name}_code_info.json")
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
                data['project_name'] = project_name
                projects.append(data)
    return projects

def create_overview_dashboard(projects, output_dir):
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    project_names = [p['project_name'] for p in projects]
    total_loc = [p['complexity']['total_loc'] for p in projects]
    doc_coverage = [p['documentation']['documentation_coverage'] * 100 for p in projects]
    contributors = [p['maintenance']['contributors'] for p in projects]
    total_commits = [p['maintenance']['total_commits'] for p in projects]
    
    ax1.bar(range(len(project_names)), total_loc, color=colors[:len(project_names)])
    ax1.set_title('Project Size (Lines of Code)', fontweight='bold')
    ax1.set_ylabel('Total LOC')
    ax1.set_xticks(range(len(project_names)))
    ax1.set_xticklabels(project_names, rotation=45, ha='right')
    
    ax2.bar(range(len(project_names)), doc_coverage, color=colors[:len(project_names)])
    ax2.set_title('Documentation Coverage', fontweight='bold')
    ax2.set_ylabel('Coverage (%)')
    ax2.set_xticks(range(len(project_names)))
    ax2.set_xticklabels(project_names, rotation=45, ha='right')
    ax2.axhline(y=50, color='red', linestyle='--', alpha=0.7)
    
    ax3.scatter(contributors, total_commits, s=100, c=colors[:len(project_names)], alpha=0.7)
    ax3.set_title('Development Activity', fontweight='bold')
    ax3.set_xlabel('Contributors')
    ax3.set_ylabel('Total Commits')
    for i, name in enumerate(project_names):
        ax3.annotate(name, (contributors[i], total_commits[i]), xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax4.scatter(total_loc, doc_coverage, s=100, c=colors[:len(project_names)], alpha=0.7)
    ax4.set_title('Project Size vs Documentation', fontweight='bold')
    ax4.set_xlabel('Lines of Code')
    ax4.set_ylabel('Documentation Coverage (%)')
    for i, name in enumerate(project_names):
        ax4.annotate(name, (total_loc[i], doc_coverage[i]), xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'project_overview_dashboard.pdf'), bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'project_overview_dashboard.png'), bbox_inches='tight')
    plt.show()

def create_complexity_analysis(projects, output_dir):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    project_names = [p['project_name'] for p in projects]
    estimated_files = [p['complexity']['total_loc'] / p['complexity']['avg_loc_per_file'] for p in projects]
    avg_file_size = [p['complexity']['avg_loc_per_file'] for p in projects]
    doc_coverage = [p['documentation']['documentation_coverage'] for p in projects]
    avg_doc_length = [p['documentation']['avg_doc_length'] for p in projects]
    
    ax1.scatter(estimated_files, avg_file_size, s=150, c=colors[:len(project_names)], alpha=0.7)
    ax1.set_title('Project Scale Analysis', fontweight='bold')
    ax1.set_xlabel('Total Files (estimated)')
    ax1.set_ylabel('Average File Size (LOC)')
    for i, name in enumerate(project_names):
        ax1.annotate(name, (estimated_files[i], avg_file_size[i]), xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax2.scatter(doc_coverage, avg_doc_length, s=150, c=colors[:len(project_names)], alpha=0.7)
    ax2.set_title('Documentation Quality Analysis', fontweight='bold')
    ax2.set_xlabel('Documentation Coverage')
    ax2.set_ylabel('Average Documentation Length')
    for i, name in enumerate(project_names):
        ax2.annotate(name, (doc_coverage[i], avg_doc_length[i]), xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'complexity_analysis.pdf'), bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'complexity_analysis.png'), bbox_inches='tight')
    plt.show()

def create_dataset_summary_table(projects, output_dir):
    data = []
    for p in projects:
        estimated_files = int(p['complexity']['total_loc'] / p['complexity']['avg_loc_per_file'])
        doc_coverage_pct = f"{p['documentation']['documentation_coverage']*100:.1f}%"
        
        data.append({
            'Project': p['project_name'],
            'LOC': p['complexity']['total_loc'],
            'Files': estimated_files,
            'Doc Coverage': doc_coverage_pct,
            'Contributors': p['maintenance']['contributors'],
            'Commits': p['maintenance']['total_commits']
        })
    
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('tight')
    ax.axis('off')
    
    table = ax.table(cellText=df.values, colLabels=df.columns, 
                    cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    # header styling
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # alternating row colors
    for i in range(1, len(df) + 1):
        for j in range(len(df.columns)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#F2F2F2')
    
    plt.title('Evaluation Dataset Summary', fontweight='bold', pad=20, fontsize=14)
    plt.savefig(os.path.join(output_dir, 'evaluation_dataset_summary.pdf'), bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'evaluation_dataset_summary.png'), bbox_inches='tight')
    plt.show()

def create_characteristics_heatmap(projects, output_dir):
    project_names = [p['project_name'] for p in projects]
    
    metrics = {
        'Size (LOC)': [p['complexity']['total_loc'] for p in projects],
        'Doc Coverage': [p['documentation']['documentation_coverage'] for p in projects],
        'Contributors': [p['maintenance']['contributors'] for p in projects],
        'Total Commits': [p['maintenance']['total_commits'] for p in projects],
        'Avg File Churn': [p['maintenance']['avg_file_churn'] for p in projects]
    }
    
    # normalize each metric to 0-1 scale
    normalized_data = []
    for metric_name, values in metrics.items():
        max_val = max(values)
        min_val = min(values)
        if max_val != min_val:
            normalized = [(v - min_val) / (max_val - min_val) for v in values]
        else:
            normalized = [0.5] * len(values)
        normalized_data.append(normalized)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    heatmap_data = np.array(normalized_data).T
    
    im = ax.imshow(heatmap_data, cmap='RdYlBu_r', aspect='auto')
    
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(list(metrics.keys()), rotation=45, ha='right')
    ax.set_yticks(range(len(project_names)))
    ax.set_yticklabels(project_names)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Normalized Value (0=Min, 1=Max)', rotation=270, labelpad=20)
    
    plt.title('Project Characteristics Heatmap', fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'characteristics_heatmap.pdf'), bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'characteristics_heatmap.png'), bbox_inches='tight')
    plt.show()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(root_dir, 'results')
    
    projects = load_all_projects(results_dir)
    
    if not projects:
        print("no project data found")
        return
    
    print(f"loaded {len(projects)} projects:")
    for p in projects:
        print(f"  - {p['project_name']}")
    
    create_overview_dashboard(projects, script_dir)
    create_complexity_analysis(projects, script_dir)
    create_dataset_summary_table(projects, script_dir)
    create_characteristics_heatmap(projects, script_dir)
    
    total_loc = sum(p['complexity']['total_loc'] for p in projects)
    avg_doc_coverage = np.mean([p['documentation']['documentation_coverage'] for p in projects]) * 100
    
    print(f"\ndataset summary:")
    print(f"total projects: {len(projects)}")
    print(f"total LOC: {total_loc:,}")
    print(f"avg documentation coverage: {avg_doc_coverage:.1f}%")

if __name__ == "__main__":
    main()
