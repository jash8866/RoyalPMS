from fastapi import FastAPI
from ai import talk

app=FastAPI()

@app.get("/")
def read_root():
    return{"message":"Hello world"}

@app.get("/ai")
def idk(msg):
    talk(msg)