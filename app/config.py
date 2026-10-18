import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey")

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
