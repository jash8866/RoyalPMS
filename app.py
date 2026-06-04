from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from ai import AIServiceError, talk
from dbcon import create_connection

app = FastAPI()
db_connection = create_connection(host="localhost", username="root", password="", db_name="royalpms/royalpms_cryst8000")
@app.get("/")
def read_root():
    return {"message": "Hello world"}

@app.get("/ai")
def idk(msg: str):
    try:
        return PlainTextResponse(talk(msg))
    except AIServiceError:
        return PlainTextResponse(
            "The AI service is temporarily unavailable. Please try again in a few moments."
        )