import ast
import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set

@dataclass
class Node:
    id: str
    name: str
    module: str
    package: str
    type: str  # "function" or "method" or "class"
    file_path: str
    start_line: int

@dataclass
class Edge:
    source: str
    target: str

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
        self.edges: Set[tuple] = set()
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
            edges=[Edge(source=s, target=t) for s, t in self.edges]
        )
        return asdict(graph)

    def _get_module_info(self, file_path: str):
        rel_path = os.path.relpath(file_path, self.project_root)
        module_path = os.path.splitext(rel_path)[0].replace(os.sep, ".")
        package = module_path.split(".")[0]
        return module_path, package

    def _scan_definitions(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            # Skip files that can't be parsed
            return

        module, package = self._get_module_info(file_path)

        # Walk to find functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Handle top-level functions
                node_id = f"{module}.{node.name}"
                self._add_node(node_id, node.name, module, package, "function", file_path, node.lineno)
                self.function_definitions[node.name] = node_id # Simple map for local resolution
                self.function_definitions[node_id] = node_id

            elif isinstance(node, ast.ClassDef):
                class_id = f"{module}.{node.name}"
                # We optionally track classes, but mainly methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_id = f"{class_id}.{item.name}"
                        self._add_node(method_id, item.name, module, package, "method", file_path, item.lineno)
                        self.function_definitions[item.name] = method_id # Ambiguous if same name diff class, simplified
                        self.function_definitions[method_id] = method_id

    def _add_node(self, id, name, module, package, type, file_path, start_line):
        if id not in self.nodes_map:
            self.nodes_map[id] = Node(id, name, module, package, type, file_path, start_line)

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
                # Push new scope
                # If inside class, we need class name... doing full recursion is cleaner
                func_id = f"{self.current_module}.{node.name}"
                # Check if it's a method... crude check: if stack has something that looks like a class?
                # Actually, in _scan_definitions we built ids correctly.
                # Let's try to reconstruct ID logic strictly or just "best effort"
                
                # Simplified: Assume top level for now or try to match what definition pass found
                # Better: keep track of Class context
                
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_ClassDef(self, node):
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Call(self, node):
                if not self.scope_stack:
                    return # Call at module level, maybe ignore or assign to module
                
                # Determine source ID
                source_suffix = ".".join(self.scope_stack)
                source_id = f"{self.current_module}.{source_suffix}"
                
                # If source_id wasn't registered in nodes_map (e.g. nested funcs or weird mismatch), 
                # we might strip parts or exact match.
                # For this MVP, let's assume standard structure: Module.Class.Method or Module.Function
                
                # Resolving Target
                target_id = self._resolve_target(node)
                if target_id and target_id in self.generator.nodes_map:
                     self.generator.edges.add((source_id, target_id))

            def _resolve_target(self, node):
                # Case 1: simple function call func()
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    # 1. Check local imports (not implemented fully yet, simplified)
                    # 2. Check global registry for unique match
                    # Assuming mostly unique names or exact relative imports standard
                    
                    # Try fully qualified if available
                    candidate = f"{self.current_module}.{name}"
                    if candidate in self.generator.nodes_map:
                        return candidate
                    
                    # Heuristic: search in all definitions (Risk: false positives)
                    # But CR requires visual, maybe better to be conservative?
                    # Let's try to find if 'name' is in our definitions map
                    # (This is very "naive", a real production System needs symbol tables)
                    for nid in self.generator.nodes_map:
                        if nid.endswith(f".{name}"):
                            # Heuristic: if it's in same package?
                            return nid
                            
                # Case 2: Attribute call obj.method()
                elif isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    # We don't know type of obj easily. 
                    # If obj is 'self', we look in current class.
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "self":
                            # Current class is second to last in scope stack?
                            if len(self.scope_stack) >= 2:
                                class_name = self.scope_stack[-2]
                                candidate = f"{self.current_module}.{class_name}.{method_name}"
                                return candidate
                        
                        # else obj.method - try to find *any* method with that name?
                        # Or if obj is a module name?
                        # e.g. os.path.join -> module os.path
                        
                return None

        visitor = CallVisitor(self, module)
        visitor.visit(tree)
