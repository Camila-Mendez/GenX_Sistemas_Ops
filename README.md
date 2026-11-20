# GenX · Portal de Recuperación ante Desastres

Aplicación web en Flask para **GenX, S.A.**, empresa que ofrece arquitecturas de recuperación ante desastres (DR) activo‑pasivo para servidores Ubuntu desde su oficina en Costa Rica.

El portal está pensado para ejecutarse **sobre la propia infraestructura DR del proyecto**: se publica en la IP virtual de keepalived y muestra qué nodo (activo o pasivo) está atendiendo, para evidenciar el failover en la demostración.

> Esta rama reutiliza la estructura y el esquema de rutas de *La Carreta del Café* (rutas públicas → login con dos tipos → panel interno / zona de cliente → flujo de solicitud), con una nueva identidad visual y persistencia real en MySQL.

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

**MySQL 8** instalado directamente en las VMs Ubuntu. El modelo físico se crea en la VM con los scripts de `sql/`, y la app solo se conecta a través de **un único script de conexión**, `app/utilities/db_connection.py`, que usa PyMySQL y ejecuta SQL directo con parámetros. No hay ORM y la app no crea tablas. Guía completa, incluida la integración con DRBD y keepalived: [docs/BASE_DE_DATOS.md](docs/BASE_DE_DATOS.md).

## Instalación rápida

En la VM, como root de MySQL (cambia antes la contraseña del script 01):

```bash
sudo mysql < sql/01_crear_bd_y_usuario.sql
sudo mysql < sql/02_modelo_fisico.sql
sudo mysql < sql/03_datos_iniciales.sql
```

La app:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # poner DB_PASSWORD y SECRET_KEY
flask --app run check-db           # prueba la conexión
flask --app run create-user admin --role admin
python run.py                      # http://127.0.0.1:5000
```

Para escuchar en la red (servidores Ubuntu): `FLASK_HOST=0.0.0.0 python run.py`.

## Pruebas

Las pruebas usan un MySQL real con una base **separada** (`genx_test`) y cargan los mismos scripts `02` y `03`. Se crea una sola vez:

```sql
CREATE DATABASE genx_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'genx_test'@'localhost' IDENTIFIED BY 'genx_test';
GRANT ALL PRIVILEGES ON genx_test.* TO 'genx_test'@'localhost';
```

```bash
pytest -q
```

Si no hay MySQL disponible, las pruebas se omiten. Para usar otros datos, define `TEST_DB_HOST`, `TEST_DB_NAME`, `TEST_DB_USER` y `TEST_DB_PASSWORD`.

## Estructura del proyecto

```text
├── app/
│   ├── static/                     # styles.css, favicon y logo
│   ├── templates/                  # vistas Jinja2
│   ├── utilities/db_connection.py  # ÚNICO acceso a MySQL (conexión + helpers SQL)
│   ├── cli.py                      # comandos check-db y create-user
│   ├── config.py                   # SECRET_KEY y nombre del nodo
│   ├── routes.py                   # rutas con consultas SQL
│   └── __init__.py
├── docs/BASE_DE_DATOS.md
├── sql/
│   ├── 01_crear_bd_y_usuario.sql
│   ├── 02_modelo_fisico.sql
│   └── 03_datos_iniciales.sql
├── tests/
├── .env.example
├── requirements.txt
└── run.py
```

## Seguridad

- Define un `SECRET_KEY` largo y aleatorio; nunca subas `.env` al repositorio.
- No ejecutes con `FLASK_DEBUG=1` en producción; para producción usa gunicorn detrás de nginx.
