from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Axenix_API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
async def check_alive():
    """
    Проверка
    """
    return {"alive": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5050)
