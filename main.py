from fastapi import FastAPI
import uvicorn
from api.thermal_insulations_handlers import router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.thermal_insulation import router as insulation_router
from api.users import router as users_router

app = FastAPI(title="Thermal Insulation App")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(insulation_router)
app.include_router(users_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
