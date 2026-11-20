# GenX · Portal de Recuperación ante Desastres

Aplicación web en Flask para **GenX, S.A.**, empresa que ofrece arquitecturas de recuperación ante desastres (DR) activo‑pasivo para servidores Ubuntu desde su oficina en Costa Rica.

El portal está pensado para ejecutarse **sobre la propia infraestructura DR del proyecto**: se publica en la IP virtual de keepalived y muestra qué nodo (activo o pasivo) está atendiendo, para evidenciar el failover en la demostración.

> Esta rama reutiliza la estructura y el esquema de rutas de *La Carreta del Café* (rutas públicas → login con dos tipos → panel interno / zona de cliente → flujo de solicitud), con una nueva identidad visual y persistencia real en base de datos.

## Funcionalidades

- Páginas públicas: inicio, servicios, nosotros y contacto (los mensajes se guardan en BD).
- Login con dos tipos de acceso, validado contra la base de datos:
  - **admin** → `/dashboard`: estado del nodo y de la BD, solicitudes (con cambio de estado), bitácora de accesos y mensajes.
  - **cliente** → `/planes`: catálogo de planes DR, solicitud (tipo carrito), confirmación y "Mis solicitudes".
- Registro de clientes; los administradores se crean por línea de comandos.
- Bitácora de login que registra qué servidor respondió cada intento.
- Endpoint `/health` (JSON, 200/503) para monitoreo o `track_script` de keepalived.
- Contraseñas con hash, protección CSRF en todos los formularios.

## Mapa de rutas

| La Carreta del Café | GenX | Acceso |
|---|---|---|
| `/`, `/aboutus`, `/contactsales` | `/`, `/nosotros`, `/servicios`, `/contacto` | público |
| `/login` (user / shopper) | `/login` (admin / cliente) | público |
| `/register` (shopper) | `/register` (cliente) | público |
| `/dashboard` | `/dashboard`, `/dashboard/solicitud/<id>/estado` | admin |
| `/shop` | `/planes` | cliente |
| `/add-to-cart`, `/cart`, `/remove-from-cart`, `/update-cart` | `/solicitud/agregar/<slug>`, `/solicitud`, `/solicitud/quitar/<slug>`, `/solicitud/actualizar/<slug>/<accion>` | cliente |
| `/checkout`, `/payment`, `/payment-success` | `/confirmar`, `/solicitud-enviada/<id>`, `/mis-solicitudes` | cliente |
| `/logout` | `/logout` | — |
| — | `/health` | público |

## Base de datos

Compatible con **PostgreSQL, MySQL/MariaDB y SQL Server** (vía SQLAlchemy). Se elige con la variable `DB_ENGINE`; sin configurar, usa SQLite local para desarrollo. Guía paso a paso: [docs/BASE_DE_DATOS.md](docs/BASE_DE_DATOS.md).

## Instalación rápida

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # editar valores
flask --app run init-db            # crea tablas y planes
flask --app run create-user admin --role admin
python run.py                      # http://127.0.0.1:5000
```

Para escuchar en la red (servidores Ubuntu): `FLASK_HOST=0.0.0.0 python run.py`.

## Pruebas

```bash
pytest -q
```

## Estructura del proyecto

```text
├── app/
│   ├── static/            # styles.css, favicon y logo
│   ├── templates/         # vistas Jinja2
│   ├── utilities/db.py    # instancia SQLAlchemy, health check, nombre del nodo
│   ├── cli.py             # comandos init-db y create-user
│   ├── config.py          # arma la cadena de conexión según DB_ENGINE
│   ├── models.py          # usuarios, planes, solicitudes, bitácora, mensajes
│   ├── routes.py
│   └── __init__.py
├── docs/BASE_DE_DATOS.md
├── sql/                   # creación de base y usuario por motor
├── tests/
├── .env.example
├── requirements.txt
└── run.py
```

## Seguridad

- Define un `SECRET_KEY` largo y aleatorio; nunca subas `.env` al repositorio.
- No ejecutes con `FLASK_DEBUG=1` en producción; para producción usa gunicorn detrás de nginx.
