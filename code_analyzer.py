import os
import fnmatch


class CodeAnalyzer:
    def __init__(self, extensions, exclude_patterns, include_tests):
        self.extensions = extensions
        self.exclude_patterns = exclude_patterns
        self.include_tests = include_tests

    def analyze_project(self, project_dir):
        all_files = self._collect_files(project_dir)
        filtered_files = self._filter_files(all_files)
        return filtered_files

    def _collect_files(self, directory):
        found_files = []
        for root, dirs, files in os.walk(directory):
            if self._should_exclude_directory(root):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                found_files.append(file_path)
        
        return found_files

    def _filter_files(self, files):
        filtered = []
        
        for file_path in files:
            if not self._has_valid_extension(file_path):
                continue
                
            if not self.include_tests and self._is_test_file(file_path):
                continue
                
            if self._should_exclude_file(file_path):
                continue
                
            filtered.append(file_path)
        
        return filtered

    def _has_valid_extension(self, file_path):
        return any(file_path.endswith(ext) for ext in self.extensions)

    def _is_test_file(self, file_path):
        filename = os.path.basename(file_path).lower()
        return 'test' in filename or file_path.lower().find('/test/') != -1

    def _should_exclude_directory(self, directory):
        return any(fnmatch.fnmatch(directory, pattern) for pattern in self.exclude_patterns)

    def _should_exclude_file(self, file_path):
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.exclude_patterns)