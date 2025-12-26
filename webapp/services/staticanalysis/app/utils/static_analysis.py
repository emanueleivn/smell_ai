import tempfile
import os
import pandas as pd
from webapp.services.staticanalysis.app.schemas.responses import Smell
from components.inspector import Inspector

OUTPUT_DIR = "output"
inspector = Inspector(output_path=OUTPUT_DIR)


def detect_static(code_snippet: str) -> dict:
    try:
        # Create a temporary file to analyze the code snippet
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w"
        ) as temp_file:
            temp_file.write(code_snippet)
            temp_file_path = temp_file.name

        smells_df: pd.DataFrame = inspector.inspect(temp_file_path)

        # Handle cases with no results
        if smells_df.empty:
            return {"success": True,
                    "response": "Static analysis returned no data"}

        smells = [
            Smell(
                function_name=row["function_name"],
                line=row["line"],
                smell_name=row["smell_name"],
                description=row["description"],
                additional_info=row["additional_info"],
            )
            for _, row in smells_df.iterrows()
        ]

        # Clean up the temporary file
        os.remove(temp_file_path)

        return {"success": True, "response": smells}

    except Exception as e:
        return {"success": False, "response": str(e)}


from components.call_graph_generator import CallGraphGenerator

def detect_static_with_graph(
    code_snippet: str | None, # Can be content or directory path
    file_path: str = None, # Optional: original file path if content is from a file
    is_directory: bool = False,
    original_filename: str = None # Optional: for single file, what name to display
):
    """
    Runs static analysis and call graph generation.
    - If is_directory is True, code_snippet is treated as the directory path.
    - If is_directory is False, code_snippet is the content (or path if file_path provided).
    """

    smells_raw_dicts = []
    project_root = None
    display_root_name = None
    target_files_for_graph = []
    
    # 1. Smell Detection
    if is_directory:
        project_root = code_snippet
        display_root_name = os.path.basename(project_root)

        for root, _, files in os.walk(project_root):
             for file in files:
                if file.endswith(".py"):
                    full_p = os.path.join(root, file)
                    target_files_for_graph.append(full_p) # Collect for graph
                    with open(full_p, 'r') as f:
                        c = f.read()
                    file_smells = _run_inspector_on_content(c)
                    rel_p = os.path.relpath(full_p, project_root)
                    
                    # Augment smells with file info
                    for s in file_smells:
                        s['file'] = rel_p # Add file info to smell
                    smells_raw_dicts.extend(file_smells)
    else:
        # Single file or snippet
        if file_path:
             # Content provided, but we have a file_path for context
             smells_raw_dicts = _run_inspector_on_content(code_snippet)
             project_root = os.path.dirname(file_path)
             display_root_name = original_filename or os.path.basename(file_path)
             target_files_for_graph.append(file_path)
        else:
             # Pure snippet, no file_path
             smells_raw_dicts = _run_inspector_on_content(code_snippet)
             project_root = None # No root for a pure snippet
             display_root_name = "snippet.py"
             # For snippet, we need to create a temp file for graph generation
             temp_file_path = None
             try:
                 with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as temp_file:
                     temp_file.write(code_snippet)
                     temp_file_path = temp_file.name
                 target_files_for_graph.append(temp_file_path)
                 project_root = os.path.dirname(temp_file_path) # Set root for temp file
             except Exception as e:
                 print(f"Error creating temp file for snippet graph: {e}")
                 # Handle error, perhaps skip graph generation for snippet
                 target_files_for_graph = []
             finally:
                 # temp_file_path will be cleaned up after graph generation
                 pass

    # Convert raw smell dictionaries to Smell objects
    smells = [
        Smell(
            function_name=s["function_name"],
            line=s["line"],
            smell_name=s["smell_name"],
            description=s["description"],
            additional_info=s["additional_info"],
            file=s.get("file") # Include file if present
        )
        for s in smells_raw_dicts
    ]

    # 2. Call Graph Generation
    graph_dict = None
    try:
        if target_files_for_graph:
            # Ensure project_root is set for CallGraphGenerator
            if not project_root and target_files_for_graph:
                # If it's a single temp file, its directory is the root
                project_root = os.path.dirname(target_files_for_graph[0])

            generator = CallGraphGenerator(project_root)
            graph_dict = generator.generate(target_files_for_graph)
            
            # Sanitize Paths in Graph
            _sanitize_graph_paths(graph_dict, project_root, replacement_name=original_filename if not is_directory else None)

    except Exception as e:
        print(f"Graph generation error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary file created for snippet if it was made
        if not is_directory and not file_path and 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {"success": True, "response": smells, "call_graph": graph_dict}


def _run_inspector_on_content(content: str):
    """
    Helper to run inspector on string content by effectively creating a temp file.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        smells_df: pd.DataFrame = inspector.inspect(tmp_path)
        
        os.remove(tmp_path)

        if smells_df.empty:
            return []
            
        return [
            {
                "function_name": row["function_name"],
                "line": row["line"],
                "smell_name": row["smell_name"],
                "description": row["description"],
                "additional_info": row["additional_info"],
            }
            for _, row in smells_df.iterrows()
        ]
    except Exception as e:
        print(f"Smell detection error: {e}")
        return []

def _sanitize_graph_paths(graph_dict: dict, root: str, replacement_name: str = None):
    """
    Modifies the graph dictionary in-place to make paths relative/clean.
    """
    if not graph_dict: return

    for node in graph_dict.get('nodes', []):
        raw_path = node.get('file_path', '')
        if root and raw_path.startswith(root):
             rel = os.path.relpath(raw_path, root)
             if replacement_name and rel == os.path.basename(raw_path):
                 node['file_path'] = replacement_name
             else:
                 node['file_path'] = rel # e.g. "subdir/file.py"
        if replacement_name:
             node['file_path'] = replacement_name
             clean_name = replacement_name.replace(".py", "")
             node['package'] = clean_name
             # Force update module name to match package/file
             # We assume single file upload has module name = filename
             node['module'] = clean_name
             
    for edge in graph_dict.get('edges', []):
         for site in edge.get('call_sites', []):
             raw_path = site.get('file_path', '')
             if root and raw_path.startswith(root):
                 rel = os.path.relpath(raw_path, root)
                 if replacement_name and rel == os.path.basename(raw_path):
                     site['file_path'] = replacement_name
                 else:
                     site['file_path'] = rel
