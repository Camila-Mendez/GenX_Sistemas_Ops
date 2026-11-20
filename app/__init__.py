from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from app.utilities import db_connection

# Carga variables desde .env (si existe) antes de leer la configuración
load_dotenv()

app = Flask(__name__)

# Cargar configuración
app.config.from_object("app.config.Config")

# Conexión a MySQL (se cierra al final de cada petición) y protección CSRF
db_connection.init_app(app)
csrf = CSRFProtect(app)

# Importar las rutas y comandos (tienen que ir después de crear app)
from app import routes, cli  # noqa: E402,F401
