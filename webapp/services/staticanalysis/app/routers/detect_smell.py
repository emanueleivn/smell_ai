from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import zipfile
import os
from pathlib import Path # Added based on existing usage in the file
from webapp.services.staticanalysis.app.schemas.requests import (
    DetectSmellRequest,
)
from webapp.services.staticanalysis.app.schemas.responses import (
   DetectSmellStaticResponse,
   DetectCallGraphResponse,
)
from webapp.services.staticanalysis.app.utils.static_analysis import (
    detect_static,
    detect_static_with_graph,
)

router = APIRouter()


@router.post("/detect_smell_static", response_model=DetectSmellStaticResponse)
async def detect_smell_static(payload: DetectSmellRequest):
    code_snippet = payload.code_snippet
    analysis_result = detect_static(code_snippet)
    return DetectSmellStaticResponse(
        success=analysis_result["success"], smells=analysis_result["response"]
    )

@router.post("/detect_call_graph", response_model=DetectCallGraphResponse)
async def detect_call_graph(
    file: UploadFile = File(None),
    code_snippet: str = Body(None),
    include_call_graph: bool = Body(True)
):
    """
    Detects code smells and optionally generates a call graph.
    Accepts either a code_snippet string OR a file (single .py or .zip).
    """
    smells = []
    graph = None

    # Handle Uploaded File (ZIP or Single Python)
    if file:
        content = await file.read()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Check if ZIP
            if file.filename.endswith(".zip"):
                 # Extract to a temp dir
                 with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Analyze the directory
                    result = detect_static_with_graph(temp_dir, is_directory=True)
                    smells = result.get("response", [])
                    graph = result.get("call_graph")
            else:
                 # Single File
                 # Read content back for sniffers if needed, or pass path
                 # For consistency with utility, we pass content + path
                 with open(tmp_path, 'r') as f:
                     text_content = f.read()
                 
                 result = detect_static_with_graph(text_content, file_path=tmp_path, original_filename=file.filename)
                 smells = result.get("response", [])
                 graph = result.get("call_graph")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # Handle Raw Code Snippet
    elif code_snippet:
        result = detect_static_with_graph(code_snippet)
        smells = result.get("response", [])
        graph = result.get("call_graph")
    
    else:
        return DetectCallGraphResponse(success=False, smells=None, call_graph=None)

    return DetectCallGraphResponse(
        success=True,
        smells=smells,
        call_graph=graph
    )
