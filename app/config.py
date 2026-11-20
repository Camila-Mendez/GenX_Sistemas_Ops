import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey-cambiar-en-produccion")
    # Nombre con el que se identifica este nodo en el panel (activo / pasivo)
    NODE_NAME = os.getenv("GENX_NODE_NAME")

# Los datos de conexión a MySQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
# se leen en app/utilities/db_connection.py
