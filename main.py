from fastapi import Depends, FastAPI

from auth import verify_adfs_token

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/testAdfs")
def test_adfs(claims: dict = Depends(verify_adfs_token)):
    return {"message": "ADFS token verified", "subject": claims.get("sub")}


@app.get("/health")
def health():
    return {"status": "ok"}
