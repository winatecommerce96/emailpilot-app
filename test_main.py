"""
Simple test version of EmailPilot API
"""
from fastapi import FastAPI

app = FastAPI(title="EmailPilot Test")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "EmailPilot Test"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)