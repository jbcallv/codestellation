import os
import re


class Chunker:
    def __init__(self, window_size, overlap_size, min_chunk_size, respect_boundaries):
        self.window_size = window_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        self.respect_boundaries = respect_boundaries

    def create_chunks(self, file_paths):
        all_chunks = []
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_chunks = self._chunk_file(file_path, content)
                all_chunks.extend(file_chunks)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return all_chunks

    def _chunk_file(self, file_path, content):
        lines = content.split('\n')
        file_imports = self._extract_imports(content)
        class_context = self._extract_class_context(content)
        
        chunks = []
        start_line = 0
        
        while start_line < len(lines):
            end_line = min(start_line + self.window_size, len(lines))
            
            if self.respect_boundaries:
                end_line = self._adjust_for_boundaries(lines, start_line, end_line)
            
            if end_line - start_line < self.min_chunk_size and end_line < len(lines):
                start_line += self.window_size - self.overlap_size
                continue
            
            chunk_lines = lines[start_line:end_line]
            chunk_content = '\n'.join(chunk_lines)
            
            chunk = {
                'file_path': file_path,
                'content': chunk_content,
                'start_line': start_line,
                'end_line': end_line,
                'imports': file_imports,
                'class_context': class_context
            }
            
            chunks.append(chunk)
            
            if end_line >= len(lines):
                break
                
            start_line = end_line - self.overlap_size
        
        return chunks

    def _extract_imports(self, content):
        import_pattern = r'^\s*import\s+([^;]+);'
        imports = []
        
        for line in content.split('\n'):
            match = re.match(import_pattern, line)
            if match:
                imports.append(match.group(1).strip())
        
        return imports

    def _extract_class_context(self, content):
        class_pattern = r'^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)'
        
        for line in content.split('\n'):
            match = re.match(class_pattern, line)
            if match:
                return match.group(1)
        
        return None

    def _adjust_for_boundaries(self, lines, start_line, end_line):
        if end_line >= len(lines):
            return end_line
        
        for i in range(end_line - 1, start_line, -1):
            line = lines[i].strip()
            
            if line.endswith('}') and not line.startswith('//'):
                return i + 1
            
            if line == '' and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (next_line.startswith('public ') or 
                    next_line.startswith('private ') or 
                    next_line.startswith('protected ') or
                    next_line.startswith('class ') or
                    next_line.startswith('@')):
                    return i + 1
        
        return end_line