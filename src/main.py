from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
from pathlib import Path

app = FastAPI()

class RunPayload(BaseModel):
    repo_url: str
    token: str

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/run")
def run_ghaminer(payload: RunPayload):
    repo = "/".join(payload.repo_url.rstrip("/").split("/")[-2:])
    print(f"[GHAminer API] Fetching data for repo: {repo}")

    ghametrics_path = Path(__file__).resolve().parent.parent / "src" / "GHAMetrics.py"

    if not ghametrics_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"GHAMetrics.py not found at: {ghametrics_path}"
        )

    try:
        result = subprocess.run(
            [
                "python3", str(ghametrics_path),
                "--token", payload.token,
                "--single-project", payload.repo_url
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "repo": repo,
            "stdout": result.stdout
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "GHAminer execution failed",
                "repo": repo,
                "stderr": e.stderr.strip()
            }
        )