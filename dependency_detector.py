import os
import re


class DependencyDetector:
    def __init__(self, project_files):
        self.project_files = project_files
        self.project_index = self._build_project_index()

    def find_dependencies(self, chunk):
        dependencies = []
        
        method_calls = self._extract_method_calls(chunk['content'])
        
        for call in method_calls:
            resolved_dep = self._resolve_dependency(call, chunk)
            if resolved_dep:
                dependencies.append(resolved_dep)
        
        return dependencies

    def _extract_method_calls(self, content):
        method_pattern = r'(\w+)\.(\w+)\s*\('
        calls = []
        
        for match in re.finditer(method_pattern, content):
            object_name = match.group(1)
            method_name = match.group(2)
            calls.append((object_name, method_name))
        
        return calls

    def _resolve_dependency(self, call, chunk):
        object_name, method_name = call
        
        # Check same file first (multiple classes)
        same_file_class = self._find_class_in_same_file(chunk['file_path'], object_name)
        if same_file_class and self._method_exists_in_class(chunk['file_path'], object_name, method_name):
            return {
                'file_path': chunk['file_path'],
                'method_name': method_name,
                'class_name': object_name
            }
        
        for import_path in chunk['imports']:
            if self._matches_import(object_name, import_path):
                target_file = self._find_file_for_import(import_path)
                if target_file and self._method_exists_in_file(target_file, method_name):
                    return {
                        'file_path': target_file,
                        'method_name': method_name,
                        'class_name': self._extract_class_from_import(import_path)
                    }
        
        same_package_file = self._find_same_package_file(chunk['file_path'], object_name)
        if same_package_file and self._method_exists_in_file(same_package_file, method_name):
            return {
                'file_path': same_package_file,
                'method_name': method_name,
                'class_name': object_name
            }
        
        return None

    def _matches_import(self, object_name, import_path):
        class_name = import_path.split('.')[-1]
        return class_name == object_name

    def _find_file_for_import(self, import_path):
        class_name = import_path.split('.')[-1]
        
        for file_path in self.project_files:
            if file_path.endswith(f'{class_name}.java'):
                return file_path
        
        return None

    def _extract_class_from_import(self, import_path):
        return import_path.split('.')[-1]

    def _find_same_package_file(self, current_file, class_name):
        current_dir = os.path.dirname(current_file)
        target_file = os.path.join(current_dir, f'{class_name}.java')
        
        if target_file in self.project_files:
            return target_file
        
        return None

    def _method_exists_in_file(self, file_path, method_name):
        if file_path not in self.project_index:
            return False
        
        return method_name in self.project_index[file_path]['methods']

    def _build_project_index(self):
        index = {}
        
        for file_path in self.project_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                classes = self._extract_classes_from_file(content)
                index[file_path] = {
                    'methods': self._extract_methods_from_file(content),
                    'classes': classes
                }
                
            except Exception:
                index[file_path] = {'methods': [], 'classes': {}}
        
        return index

    def _extract_methods_from_file(self, content):
        method_pattern = r'(?:public|private|protected|static|\s)+[\w\<\>\[\]]+\s+(\w+)\s*\([^)]*\)\s*\{'
        methods = []
        
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            if method_name not in ['if', 'while', 'for', 'catch', 'switch']:
                methods.append(method_name)
        
        return methods

    def extract_method_from_file(self, file_path, method_name):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            method_lines = []
            in_method = False
            brace_count = 0
            
            for line in lines:
                if not in_method and method_name in line and '(' in line:
                    if re.search(rf'\b{method_name}\s*\(', line):
                        in_method = True
                        method_lines.append(line)
                        brace_count += line.count('{') - line.count('}')
                        continue
                
                if in_method:
                    method_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    
                    if brace_count <= 0:
                        break
            
            return '\n'.join(method_lines)
            
        except Exception:
            return f"// Could not extract method {method_name} from {file_path}"

    def _extract_classes_from_file(self, content):
        class_pattern = r'^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)'
        classes = {}
        
        for line_num, line in enumerate(content.split('\n')):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                classes[class_name] = line_num
        
        return classes

    def _find_class_in_same_file(self, file_path, class_name):
        if file_path not in self.project_index:
            return False
        
        return class_name in self.project_index[file_path]['classes']

    def _method_exists_in_class(self, file_path, class_name, method_name):
        if not self._find_class_in_same_file(file_path, class_name):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            class_start = self.project_index[file_path]['classes'][class_name]
            
            in_target_class = False
            brace_count = 0
            
            for i in range(class_start, len(lines)):
                line = lines[i]
                
                if not in_target_class and f'class {class_name}' in line:
                    in_target_class = True
                
                if in_target_class:
                    brace_count += line.count('{') - line.count('}')
                    
                    if method_name in line and '(' in line:
                        if re.search(rf'\b{method_name}\s*\(', line):
                            return True
                    
                    if brace_count <= 0 and i > class_start:
                        break
            
            return False
            
        except Exception:
            return False