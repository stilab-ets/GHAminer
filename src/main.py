from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

class RunPayload(BaseModel):
    repo_url: str
    token: str

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/run")
@app.post("/run")
def run_ghaminer(payload: RunPayload):
    repo = payload.repo_url.split("/")[-2] + "/" + payload.repo_url.split("/")[-1]
    print(f"[GHAminer1 API] Fetching data for repo: {repo}")  # 👈 add this line

    try:
        result = subprocess.run(
            [
                "python", "GHAMetrics.py",
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
                "error": "GHAminer1 execution failed",
                "repo": repo,
                "stderr": e.stderr.strip()
            }
        )