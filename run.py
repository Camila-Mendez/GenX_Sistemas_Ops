import os

from app import app

if __name__ == "__main__":
    # En los servidores Ubuntu se escucha en 0.0.0.0 para que la IP virtual (keepalived) llegue a Flask.
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
