from flask import Flask

app = Flask(__name__)

# Cargar configuración
app.config.from_object("app.config.Config")

# Importar las rutas (tienen que ir después de crear app)
from app import routes