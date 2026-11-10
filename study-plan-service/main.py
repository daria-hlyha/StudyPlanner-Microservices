from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Study Plan Service is running"}
