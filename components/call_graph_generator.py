import ast
import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Any

@dataclass
class Node:
    id: str
    name: str
    module: str
    package: str
    type: str  # "function" or "method" or "class"
    file_path: str
    start_line: int
    end_line: int
    source_code: str = "" 

@dataclass
class CallSite:
    file_path: str
    line: int
    snippet: str

@dataclass
class Edge:
    source: str
    target: str
    call_sites: List[CallSite] = field(default_factory=list)

@dataclass
class CallGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

class CallGraphGenerator:
    """
    Generates a call graph for the analyzed project.
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.nodes_map: Dict[str, Node] = {}  # id -> Node
        self.edges_map: Dict[tuple, Edge] = {} # (source, target) -> Edge
        self.function_definitions: Dict[str, str] = {} # partial_name -> full_id (simplified mapping)

    def generate(self, file_paths: List[str]) -> Dict:
        """
        Generates the call graph JSON structure.
        """
        # Pass 1: Collect definitions (Nodes)
        for file_path in file_paths:
            self._scan_definitions(file_path)

        # Pass 2: Collect calls (Edges)
        for file_path in file_paths:
            self._scan_calls(file_path)

        # Build output
        graph = CallGraph(
            nodes=list(self.nodes_map.values()),
            edges=list(self.edges_map.values())
        )
        return asdict(graph)

    def _get_module_info(self, file_path: str):
        try:
            rel_path = os.path.relpath(file_path, self.project_root)
        except ValueError:
            # Fallback if file_path is not under project_root (e.g. temp file)
            rel_path = os.path.basename(file_path)
            
        module_path = os.path.splitext(rel_path)[0].replace(os.sep, ".")
        package = module_path.split(".")[0]
        return module_path, package

    def _get_line_snippet(self, file_path: str, line: int) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if 1 <= line <= len(lines):
                    return lines[line - 1].strip()
        except:
            pass
        return ""

    def _get_source_segment(self, file_path: str, start: int, end_line: int) -> str:
        try:
             with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 1-based indexing
                if 1 <= start <= end_line <= len(lines):
                    return "".join(lines[start-1:end_line])
        except:
            pass
        return "Source not available"

    def _scan_definitions(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            return

        module, package = self._get_module_info(file_path)

        class DefinitionVisitor(ast.NodeVisitor):
            def __init__(self, generator, module, package, file_path):
                self.generator = generator
                self.module = module
                self.package = package
                self.file_path = file_path

            def visit_FunctionDef(self, node):
                # Top level function
                node_id = f"{self.module}.{node.name}"
                self.generator._add_node(node_id, node.name, self.module, self.package, "function", self.file_path, node.lineno, node.end_lineno)
                self.generator.function_definitions[node.name] = node_id 
                self.generator.function_definitions[node_id] = node_id
                # Do NOT compare self in generic_visit if we don't want inner functions
                # but we usually do. However, inner functions shouldn't be top level nodes unless we distinct them
                # For now, let's keep it simple: visit children
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                class_id = f"{self.module}.{node.name}"
                
                # Visit methods explicitly
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_id = f"{class_id}.{item.name}"
                        self.generator._add_node(method_id, item.name, self.module, self.package, "method", self.file_path, item.lineno, item.end_lineno)
                        self.generator.function_definitions[item.name] = method_id 
                        self.generator.function_definitions[method_id] = method_id
                
                
                pass 

        visitor = DefinitionVisitor(self, module, package, file_path)
        visitor.visit(tree)

    def _add_node(self, id, name, module, package, type, file_path, start_line, end_line):
        if id not in self.nodes_map:
            source = self._get_source_segment(file_path, start_line, end_line)
            self.nodes_map[id] = Node(id, name, module, package, type, file_path, start_line, end_line, source)

    def _add_edge(self, source, target, file_path, line):
        key = (source, target)
        if key not in self.edges_map:
            self.edges_map[key] = Edge(source=source, target=target)
        
        snippet = self._get_line_snippet(file_path, line)
        self.edges_map[key].call_sites.append(CallSite(file_path=file_path, line=line, snippet=snippet))

    def _scan_calls(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            return

        module, package = self._get_module_info(file_path)
        
        # Track current scope (function/method being analyzed)
        current_scope = None

        class CallVisitor(ast.NodeVisitor):
            def __init__(self, generator, current_module):
                self.generator = generator
                self.current_module = current_module
                self.scope_stack = [] # Stack of function names (ids)

            def visit_FunctionDef(self, node):
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_ClassDef(self, node):
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Call(self, node):
                if not self.scope_stack:
                    return 
                
                # Determine source ID (Simplified)
                source_suffix = ".".join(self.scope_stack)
                source_id = f"{self.current_module}.{source_suffix}"
                
                # Resolving Target
                target_id = self._resolve_target(node)
                if target_id and target_id in self.generator.nodes_map:
                     self.generator._add_edge(source_id, target_id, file_path, node.lineno)

            def _resolve_target(self, node):
                # Case 1: simple function call func() or Class()
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    candidate = f"{self.current_module}.{name}"
                    
                    # Exact local match
                    if candidate in self.generator.nodes_map:
                        return candidate
                    
                    # Heuristic: Suffix match (e.g. imported function)
                    # Also checking for Class instantiation (linking to __init__)
                    for nid in self.generator.nodes_map:
                        if nid.endswith(f".{name}"):
                            return nid
                        if nid.endswith(f".{name}.__init__"):
                             return nid

                            
                # Case 2: Attribute call obj.method()
                elif isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    
                    # 2a. Self.method()
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "self":
                            if len(self.scope_stack) >= 2:
                                class_name = self.scope_stack[-2]
                                candidate = f"{self.current_module}.{class_name}.{method_name}"
                                return candidate
                    
                    # 2b. Heuristic: Unique Method Name Analysis
                    # If 'method_name' exists in EXACTLY ONE node in the entire graph, link it.
                    # This helps resolve instance.method() calls without full type inference.
                    matches = [nid for nid in self.generator.nodes_map if nid.endswith(f".{method_name}")]
                    if len(matches) == 1:
                        return matches[0]

                return None

        visitor = CallVisitor(self, module)
        visitor.visit(tree)
