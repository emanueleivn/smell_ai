import unittest
import os
import shutil
import tempfile
from components.call_graph_generator import CallGraphGenerator

class TestCallGraphGenerator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create dummy file structure
        self.file_structure = {
            "module_a.py": """
def func_a():
    pass
""",
            "module_b.py": """
from module_a import func_a

def func_b():
    func_a()
    
class MyClass:
    def method_c(self):
        func_b()

    def method_d(self):
        self.method_c()
"""
        }
        
        for filename, content in self.file_structure.items():
            path = os.path.join(self.test_dir, filename)
            with open(path, "w") as f:
                f.write(content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_nodes_and_edges(self):
        generator = CallGraphGenerator(self.test_dir)
        files = [os.path.join(self.test_dir, f) for f in self.file_structure.keys()]
        
        graph = generator.generate(files)
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        # Verify Nodes
        node_ids = {n["id"] for n in nodes}
        self.assertIn("module_a.func_a", node_ids)
        self.assertIn("module_b.func_b", node_ids)
        self.assertIn("module_b.MyClass.method_c", node_ids)
        self.assertIn("module_b.MyClass.method_d", node_ids)
        
        # Verify Edges
        edge_set = {(e["source"], e["target"]) for e in edges}
        
        # func_b -> func_a
        self.assertIn(("module_b.func_b", "module_a.func_a"), edge_set)
        
        # method_c -> func_b
        self.assertIn(("module_b.MyClass.method_c", "module_b.func_b"), edge_set)
        
        # method_d -> method_c (self.method_c())
        self.assertIn(("module_b.MyClass.method_d", "module_b.MyClass.method_c"), edge_set)

if __name__ == '__main__':
    unittest.main()
