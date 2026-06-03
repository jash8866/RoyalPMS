from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ai import talk

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello world"}

@app.get("/ai")
def idk(msg: str):
    return StreamingResponse(talk(msg), media_type="text/plain")