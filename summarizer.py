import threading
from collections import defaultdict
from llm_client import summarize_chunk, summarize_method, summarize_file


class SummarizerAgent:
    def __init__(self, dependency_detector, shared_cache, max_dependency_context, shared_file_summaries):
        self.dependency_detector = dependency_detector
        self.shared_cache = shared_cache
        self.max_dependency_context = max_dependency_context
        self.shared_file_summaries = shared_file_summaries
        self.file_chunks = defaultdict(list)
        self.lock = threading.Lock()

    def process_chunk(self, chunk):
        dependencies = self.dependency_detector.find_dependencies(chunk)
        context = self._gather_dependency_context(dependencies)
        
        chunk_summary = summarize_chunk(chunk['content'], context)
        
        with self.lock:
            self.file_chunks[chunk['file_path']].append({
                'summary': chunk_summary,
                'start_line': chunk['start_line'],
                'end_line': chunk['end_line']
            })
            
            if self._is_file_complete(chunk['file_path']):
                file_summary = self._generate_file_summary(chunk['file_path'])
                self.shared_file_summaries[chunk['file_path']] = file_summary
                print(f"Completed file summary for {chunk['file_path']}")
                return chunk_summary, file_summary
            else:
                return chunk_summary, None
        
        return chunk_summary, None

    def _gather_dependency_context(self, dependencies):
        context_parts = []
        
        for dep in dependencies[:self.max_dependency_context]:
            method_key = f"{dep['file_path']}::{dep['class_name']}::{dep['method_name']}"
            
            method_summary = self.shared_cache.get_or_compute(
                method_key,
                lambda: self._summarize_dependency_method(dep)
            )
            
            if method_summary:
                context_parts.append(method_summary)
        
        return '\n'.join(context_parts)

    def _summarize_dependency_method(self, dependency):
        method_content = self.dependency_detector.extract_method_from_file(
            dependency['file_path'], 
            dependency['method_name']
        )
        
        return summarize_method(
            method_content, 
            dependency['file_path'], 
            dependency['method_name']
        )

    def _is_file_complete(self, file_path):
        return len(self.file_chunks[file_path]) >= self._get_expected_chunks(file_path)

    def _get_expected_chunks(self, file_path):
        if not hasattr(self, '_expected_chunks'):
            return 1
        return self._expected_chunks.get(file_path, 1)

    def set_expected_chunks(self, file_path, count):
        if not hasattr(self, '_expected_chunks'):
            self._expected_chunks = {}
        self._expected_chunks[file_path] = count

    def _generate_file_summary(self, file_path):
        chunks = sorted(self.file_chunks[file_path], key=lambda x: x['start_line'])
        chunk_summaries = [chunk['summary'] for chunk in chunks]
        
        return summarize_file(chunk_summaries, file_path)

    def get_all_file_summaries(self):
        return dict(self.shared_file_summaries)


class SharedCache:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
        self.pending = set()

    def get_or_compute(self, key, compute_func):
        with self.lock:
            if key in self.cache:
                return self.cache[key]
            
            if key in self.pending:
                return None
            
            self.pending.add(key)
        
        try:
            result = compute_func()
            
            with self.lock:
                self.cache[key] = result
                self.pending.discard(key)
            
            return result
            
        except Exception:
            with self.lock:
                self.pending.discard(key)
            return None