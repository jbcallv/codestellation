import json
import time
import threading
from collections import defaultdict
from pathlib import Path

class StatsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.llm_calls = defaultdict(int)
        self.dependency_extractions = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.dependencies_found = 0
        self.dependencies_resolved = 0
        self.start_time = None
        self.end_time = None
        
    def log_llm_call(self, category):
        with self.lock:
            self.llm_calls[category] += 1
    
    def log_dependency_extracted(self):
        with self.lock:
            self.dependency_extractions += 1
    
    def log_cache_hit(self):
        with self.lock:
            self.cache_hits += 1
    
    def log_cache_miss(self):
        with self.lock:
            self.cache_misses += 1
    
    def log_dependency_found(self):
        with self.lock:
            self.dependencies_found += 1
    
    def log_dependency_resolved(self):
        with self.lock:
            self.dependencies_resolved += 1
    
    def start_timing(self):
        self.start_time = time.time()
    
    def end_timing(self):
        self.end_time = time.time()
    
    def export_stats(self, project_name, output_dir="stats"):
        Path(output_dir).mkdir(exist_ok=True)
        
        stats = {
            "project": project_name,
            "llm_calls": dict(self.llm_calls),
            "total_llm_calls": sum(self.llm_calls.values()),
            "dependency_extractions": self.dependency_extractions,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "dependencies_found": self.dependencies_found,
            "dependencies_resolved": self.dependencies_resolved,
            "dependency_resolution_rate": self.dependencies_resolved / self.dependencies_found if self.dependencies_found > 0 else 0,
            "total_time_seconds": self.end_time - self.start_time if self.start_time and self.end_time else 0
        }
        
        output_file = Path(output_dir) / f"{project_name}_stats.json"
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return output_file

stats = StatsCollector()
