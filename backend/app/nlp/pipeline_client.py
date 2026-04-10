"""NLP pipeline adapter for in-process execution."""

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Force reload trigger - subprocess approach


class NLPPipelineClient:
    """Wraps the NLP pipeline as an in-process service."""

    def __init__(self) -> None:
        self._pipeline_fn = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        
        # Build absolute path - pipeline is a sibling of backend
        backend_root = Path(__file__).parent.parent.parent  # app/nlp/pipeline_client.py -> backend
        project_root = backend_root.parent  # backend -> root
        
        # Verify pipeline exists
        pipeline_dir = project_root / settings.NLP_PIPELINE_PATH
        if not (pipeline_dir / "pipeline.py").exists():
            raise RuntimeError(f"NLP pipeline not found at {pipeline_dir / 'pipeline.py'}")
        
        # Try to import the pipeline directly to avoid subprocess issues
        self._pipeline_dir = str(pipeline_dir)
        try:
            # Add pipeline directory to path
            import sys
            if str(pipeline_dir) not in sys.path:
                sys.path.insert(0, str(pipeline_dir))
            if str(pipeline_dir.parent) not in sys.path:
                sys.path.insert(0, str(pipeline_dir.parent))
            
            # Import the pipeline module
            import pipeline
            self._pipeline_fn = self._run_pipeline_direct
            logger.info("NLP pipeline loaded directly from %s", pipeline_dir / "pipeline.py")
            
        except ImportError as e:
            logger.warning("Direct import failed (%s), falling back to subprocess", e)
            # Use subprocess as fallback
            self._pipeline_fn = self._run_pipeline_subprocess
        
        self._loaded = True

    def _run_pipeline_direct(self, transcript_text: str) -> dict[str, Any]:
        """Run pipeline directly in the same process."""
        try:
            import pipeline
            result = pipeline.run_pipeline(transcript_text)
            return result
        except Exception as e:
            logger.error("Direct pipeline execution failed: %s", e, exc_info=True)
            raise RuntimeError(f"Pipeline execution failed: {e}")

    def _run_pipeline_subprocess(self, transcript_text: str) -> dict[str, Any]:
        """Run pipeline via subprocess to avoid import issues."""
        import subprocess
        import json
        import tempfile
        import os
        
        # Create a temporary script that imports and runs the pipeline
        script_content = f'''
import sys
import os
import json
import logging
import io
from contextlib import redirect_stdout, redirect_stderr

# Suppress all logging to avoid interfering with JSON output
logging.getLogger().setLevel(logging.CRITICAL)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)

# Add the pipeline directory to Python path
pipeline_dir = r"{self._pipeline_dir}"
sys.path.insert(0, pipeline_dir)
sys.path.insert(0, os.path.dirname(pipeline_dir))

# Change to pipeline directory to ensure relative imports work
os.chdir(pipeline_dir)

# Set environment to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    from pipeline import run_pipeline
    
    # Capture the result while suppressing intermediate output
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        result = run_pipeline({repr(transcript_text)})
    
    # Print result as JSON to stdout
    print(json.dumps(result))
    
except Exception as e:
    import traceback
    error_result = {{"error": str(e), "traceback": traceback.format_exc()}}
    print(json.dumps(error_result))
'''
        
        try:
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_script_path = f.name
            
            # Run the script
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self._pipeline_dir  # Set working directory to pipeline dir
            )
            
            # Clean up temp file
            os.unlink(temp_script_path)
            
            if result.returncode != 0:
                error_msg = f"Return code: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}"
                raise RuntimeError(f"Pipeline subprocess failed: {error_msg}")
            
            output = result.stdout.strip()
            if not output:
                raise RuntimeError("Pipeline subprocess returned no output")
            
            parsed = json.loads(output)
            if "error" in parsed:
                raise RuntimeError(f"Pipeline execution error: {parsed['error']}")
            
            return parsed
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Pipeline execution timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON output from pipeline: {e}, output: {result.stdout if 'result' in locals() else 'N/A'}")
            raise RuntimeError(f"Invalid JSON output from pipeline: {e}, output: {result.stdout if 'result' in locals() else 'N/A'}")
            
            output = result.stdout.strip()
            if not output:
                raise RuntimeError("Pipeline subprocess returned no output")
            
            parsed = json.loads(output)
            if "error" in parsed:
                raise RuntimeError(f"Pipeline execution error: {parsed['error']}")
            
            return parsed
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Pipeline execution timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON output from pipeline: {e}, output: {result.stdout if 'result' in locals() else 'N/A'}")

    def process(self, transcript_text: str) -> dict[str, Any]:
        """
        Run NLP pipeline and return a dict with 'summary' and 'action_items'.
        """
        self._load()
        if self._pipeline_fn is None:
            raise RuntimeError("NLP pipeline function was not loaded")
        result = self._pipeline_fn(transcript_text)
        if isinstance(result, str):
            result = json.loads(result)
        return result


# Module-level singleton
nlp_client = NLPPipelineClient()
