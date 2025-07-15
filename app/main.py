from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "NetMon Box is running"}
