from fastapi import FastAPI

from ai_companion.interfaces.telegram.telegram_response import telegram_router

# Initializes a FastAPI instance that will serve as the web server
app = FastAPI()
app.include_router(telegram_router)