import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from config import CHUNKING_CONFIG, PROJECT_CONFIG, SUMMARIZER_CONFIG
from code_analyzer import CodeAnalyzer
from chunk_processor import Chunker
from dependency_detector import DependencyDetector
from summarizer import SummarizerAgent, SharedCache
from llm_client import summarize_project


class SimpleSummarizer:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.shared_cache = SharedCache()
        
    def run(self):
        print(f"Starting analysis of {self.project_dir}")
        
        analyzer = CodeAnalyzer(
            PROJECT_CONFIG["supported_extensions"],
            PROJECT_CONFIG["exclude_patterns"], 
            PROJECT_CONFIG["include_test_files"]
        )
        
        java_files = analyzer.analyze_project(self.project_dir)
        print(f"Found {len(java_files)} Java files")
        
        chunker = Chunker(
            CHUNKING_CONFIG["window_size"],
            CHUNKING_CONFIG["overlap_size"],
            CHUNKING_CONFIG["min_chunk_size"],
            CHUNKING_CONFIG["respect_boundaries"]
        )
        
        chunks = chunker.create_chunks(java_files)
        print(f"Created {len(chunks)} chunks")
        
        dependency_detector = DependencyDetector(java_files)
        shared_file_summaries = {}
        
        file_chunk_counts = defaultdict(int)
        for chunk in chunks:
            file_chunk_counts[chunk['file_path']] += 1
        
        summarizer_agents = []
        for i in range(SUMMARIZER_CONFIG["max_workers"]):
            agent = SummarizerAgent(
                dependency_detector, 
                self.shared_cache,
                SUMMARIZER_CONFIG["max_dependency_context"],
                shared_file_summaries
            )
            summarizer_agents.append(agent)
        
        # Set expected chunks for all agents
        for agent in summarizer_agents:
            for file_path, count in file_chunk_counts.items():
                agent.set_expected_chunks(file_path, count)
        
        print(f"Processing chunks with {len(summarizer_agents)} workers...")
        
        # Group chunks by file
        chunks_by_file = defaultdict(list)
        for chunk in chunks:
            chunks_by_file[chunk['file_path']].append(chunk)
        
        # Assign each file to a worker
        file_assignments = {}
        for i, file_path in enumerate(chunks_by_file.keys()):
            worker_index = i % len(summarizer_agents)
            file_assignments[file_path] = worker_index
        
        with ThreadPoolExecutor(max_workers=SUMMARIZER_CONFIG["max_workers"]) as executor:
            futures = []
            
            for file_path, file_chunks in chunks_by_file.items():
                worker_index = file_assignments[file_path]
                agent = summarizer_agents[worker_index]
                
                for chunk in file_chunks:
                    future = executor.submit(agent.process_chunk, chunk)
                    futures.append(future)
            
            completed_chunks = 0
            for future in futures:
                chunk_summary, file_summary = future.result()
                completed_chunks += 1
                
                if completed_chunks % 10 == 0:
                    print(f"Processed {completed_chunks}/{len(chunks)} chunks")
                
                if file_summary:
                    print(f"Completed file summary for a file")
        
        all_file_summaries = shared_file_summaries
        
        print(f"Generated summaries for {len(all_file_summaries)} files")
        
        project_summary = summarize_project(
            list(all_file_summaries.values()), 
            self.project_dir
        )
        
        return {
            'project_summary': project_summary,
            'file_summaries': all_file_summaries,
            'total_files': len(java_files),
            'total_chunks': len(chunks),
            'project_path': self.project_dir
        }


def main():
    project_dir = "test/guava/guava" #input("Enter project directory path: ").strip()
    
    if not os.path.exists(project_dir):
        print(f"Directory {project_dir} does not exist")
        return
    
    summarizer = SimpleSummarizer(project_dir)
    results = summarizer.run()

    output_file = f"summary_{os.path.basename(project_dir)}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("PROJECT SUMMARY")
    print("="*80)
    print(results['project_summary'])
    
    print(f"\nProcessed {results['total_files']} files in {results['total_chunks']} chunks")
    print(f"Generated {len(results['file_summaries'])} file summaries")


if __name__ == "__main__":
    main()
