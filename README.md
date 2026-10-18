#La Carreta de Café - Web App con Python Flask

```markdown
# La Carreta del Café

Aplicación web desarrollada con Flask para una tienda de café. Incluye páginas informativas, inicio de sesión, catálogo, carrito y un flujo de compra de demostración.

## Funcionalidades

- Páginas de inicio, información de la empresa y contacto.
- Inicio de sesión y registro de compradores.
- Catálogo de productos de café.
- Carrito de compras con opción de agregar, quitar y cambiar cantidades.
- Checkout con datos de envío.
- Flujo de pago simulado para mostrar los estados de compra exitosa o fallida.
- Panel de dashboard para el rol de usuario interno.

## Tecnologías

- Python
- Flask
- Jinja2
- Flask-WTF
- SQL Server y `pyodbc` contemplados para una futura integración

## Requisitos

- Python instalado.
- Git, si vas a clonar el repositorio.
- En Windows, el controlador ODBC para SQL Server será necesario cuando se integre la persistencia con la base de datos.

## Instalación y ejecución en Windows

Clona el repositorio y entra en su carpeta:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd LaCarretadelcafe
```

Crea y activa un entorno virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Inicia la aplicación:

```powershell
python run.py
```

Luego abre en el navegador la dirección local que Flask muestre en la terminal, normalmente:

```text
http://127.0.0.1:5000/
```

## Estructura del proyecto

```text
LaCarretadelcafe/
├── app/
│   ├── static/
│   │   ├── img/
│   │   └── styles.css
│   ├── templates/
│   ├── utilities/
│   │   └── db_connection.py
│   ├── config.py
│   ├── routes.py
│   └── __init__.py
├── requirements.txt
└── run.py
```

## Estado actual de la aplicación

La aplicación es una demostración funcional de la tienda. Por el momento:

- Los usuarios y productos se gestionan con datos definidos en el código.
- El carrito y los datos temporales de compra se guardan en la sesión de Flask.
- El resultado del pago se simula; no se conecta a una pasarela real.
- Las rutas de la aplicación aún no guardan usuarios, productos, pedidos ni pagos en una base de datos.
- Existe un módulo de conexión preparado para SQL Server, pero todavía no forma parte del flujo de la aplicación.

## Configuración y seguridad

La aplicación puede leer `SECRET_KEY` desde las variables de entorno. Antes de desplegarla, configura una clave secreta segura y evita usar los valores de desarrollo.

El módulo de conexión a SQL Server espera las variables de entorno `DB_SERVER`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. No guardes credenciales reales en el repositorio. El archivo `.env` no se carga automáticamente con la configuración actual; si decides usarlo, tendrás que configurar explícitamente su carga.

No ejecutes la aplicación con el modo de depuración habilitado en un entorno de producción.

## Próximos pasos

- Definir e integrar los modelos de datos de la aplicación.
- Conectar las rutas con SQL Server.
- Persistir usuarios, productos, inventario, pedidos, pagos y envíos.
- Añadir validaciones y pruebas para los flujos de registro y compra.
- Integrar una pasarela de pago real cuando corresponda.
```
