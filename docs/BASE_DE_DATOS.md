# Conexión del login a la base de datos

El login, el registro y todo el portal usan SQLAlchemy, así que el mismo código funciona con los tres motores. Solo cambian el driver y las variables de entorno.

| Motor | `DB_ENGINE` | Puerto | Driver Python | Script de creación |
|---|---|---|---|---|
| PostgreSQL | `postgresql` | 5432 | psycopg2-binary | `sql/postgresql.sql` |
| MySQL / MariaDB | `mysql` | 3306 | PyMySQL | `sql/mysql.sql` |
| SQL Server | `sqlserver` | 1433 | pyodbc + ODBC Driver 18 | `sql/sqlserver.sql` |

**Recomendación para el proyecto:** PostgreSQL o MariaDB. Se instalan con `apt` en Ubuntu Server, consumen pocos recursos en las VMs y su directorio de datos se puede colocar sobre el volumen DRBD. SQL Server en Linux funciona, pero requiere 2 GB de RAM como mínimo y el repositorio de Microsoft.

## 1. Instalar el motor (servidor activo y pasivo)

```bash
# PostgreSQL
sudo apt install -y postgresql
# MySQL / MariaDB
sudo apt install -y mariadb-server
# SQL Server: seguir la guía oficial de Microsoft para Ubuntu (mssql-server + mssql-tools18 + msodbcsql18)
```

## 2. Crear la base y el usuario

Edita la contraseña en el script correspondiente y ejecútalo:

```bash
sudo -u postgres psql -f sql/postgresql.sql     # PostgreSQL
sudo mysql < sql/mysql.sql                      # MySQL / MariaDB
sqlcmd -S localhost -U sa -C -i sql/sqlserver.sql   # SQL Server
```

Si la app se conecta desde otra máquina, habilita conexiones remotas (`listen_addresses` + `pg_hba.conf` en PostgreSQL, `bind-address` en MariaDB) y abre el puerto solo para la subred interna:

```bash
sudo ufw allow from 10.0.0.0/24 to any port 5432 proto tcp
```

## 3. Configurar `.env`

```env
DB_ENGINE=postgresql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=genx_portal
DB_USER=genx_app
DB_PASSWORD=la-contraseña-del-paso-2
SECRET_KEY=una-clave-larga-y-aleatoria
```

También puedes usar una sola variable, `DATABASE_URL`, por ejemplo:
- `postgresql+psycopg2://genx_app:clave@10.0.0.10:5432/genx_portal`
- `mysql+pymysql://genx_app:clave@10.0.0.10:3306/genx_portal?charset=utf8mb4`
- `mssql+pyodbc://genx_app:clave@10.0.0.10:1433/genx_portal?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes`

## 4. Crear tablas y usuarios

```bash
flask --app run init-db                          # tablas + planes (se puede repetir)
flask --app run create-user admin --role admin   # pide correo, nombre y contraseña
```

Tablas creadas: `usuarios`, `bitacora_login`, `planes`, `solicitudes`, `solicitud_detalle`, `mensajes_contacto`.

Comprueba la conexión en `http://<servidor>:5000/health`, que debe responder `{"database": "ok", ...}`.

## 5. Cómo encaja con la arquitectura DR

- **Datos en DRBD:** monta el dispositivo DRBD (p. ej. `/dev/drbd0` en `/srv/data`) y coloca allí el directorio de datos del motor. Así la BD se replica en tiempo real al servidor pasivo.
- **Un solo motor activo:** el servicio de base de datos solo debe correr en el nodo que tiene DRBD como *Primary*. Los scripts `notify_master` / `notify_backup` de keepalived deben promover DRBD, montar el volumen e iniciar o detener la BD y la app.
- **IP virtual:** la app y los clientes usan la IP virtual (`10.0.0.10`), no la IP de cada nodo. `pool_pre_ping` ya descarta las conexiones que quedan rotas después del cambio.
- **Health check:** keepalived puede vigilar la app:
  ```conf
  vrrp_script chk_genx {
      script "/usr/bin/curl -fs http://127.0.0.1:5000/health"
      interval 3
      fall 2
  }
  ```
- **Evidencia del failover:** el panel muestra "Atendido por <nodo>" (usa `GENX_NODE_NAME` o el hostname). En la bitácora de accesos se ve qué nodo respondió cada login, antes y después de apagar el servidor activo.
- **Respaldos:** además de DRBD, programa un volcado lógico con cron, por ejemplo `pg_dump genx_portal > /backup/genx_$(date +%F).sql`, y sincronízalo con rsync.
