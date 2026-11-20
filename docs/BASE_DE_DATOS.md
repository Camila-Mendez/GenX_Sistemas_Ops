# Base de datos MySQL en las VMs

La base de datos **MySQL 8** corre directamente en los servidores Ubuntu (activo y pasivo). El trabajo se reparte así:

| Qué | Dónde | Quién lo ejecuta |
|---|---|---|
| Base de datos y usuario | `sql/01_crear_bd_y_usuario.sql` | root de MySQL, en la VM |
| Modelo físico (tablas, llaves, índices) | `sql/02_modelo_fisico.sql` | root de MySQL, en la VM |
| Datos iniciales (planes) | `sql/03_datos_iniciales.sql` | root de MySQL, en la VM |
| Conexión de la app | `app/utilities/db_connection.py` | la app (usuario `genx_app`) |

La app **no crea ni modifica tablas**. El usuario `genx_app` solo tiene `SELECT, INSERT, UPDATE, DELETE`; cualquier cambio al modelo físico se hace editando los scripts y ejecutándolos en la VM.

## Modelo físico

```text
usuarios (id PK, username UQ, email UQ, full_name, company, password_hash, role, created_at, last_login)
   │ 1
   │
   │ N
solicitudes (id PK, user_id FK→usuarios, site, contact_phone, notes, status, total_monthly, created_at)
   │ 1
   │
   │ N
solicitud_detalle (id PK, request_id FK→solicitudes [CASCADE], plan_id FK→planes, servers, unit_price)
                                                                   │ N
                                                                   │
                                                                   │ 1
planes (id PK, slug UQ, name, description, rto, rpo, price_monthly, active)

bitacora_login (id PK, username, success, node, ip_address, created_at)     -- sin FK: guarda también intentos fallidos
mensajes_contacto (id PK, name, email, company, message, created_at)
```

## 1. Instalar MySQL (en los dos servidores)

```bash
sudo apt update && sudo apt install -y mysql-server
```

```bash
sudo mysql_secure_installation
```

## 2. Ejecutar los scripts (una sola vez, en el servidor activo)

Antes, cambia la contraseña en `sql/01_crear_bd_y_usuario.sql`.

```bash
sudo mysql < sql/01_crear_bd_y_usuario.sql
```

```bash
sudo mysql < sql/02_modelo_fisico.sql
```

```bash
sudo mysql < sql/03_datos_iniciales.sql
```

Los tres scripts se pueden volver a ejecutar sin romper nada: usan `IF NOT EXISTS`, y los planes se actualizan con `ON DUPLICATE KEY UPDATE`. `CREATE USER IF NOT EXISTS` no cambia la contraseña de un usuario que ya existe; para cambiarla:

```sql
ALTER USER 'genx_app'@'localhost' IDENTIFIED BY 'nueva-clave';
ALTER USER 'genx_app'@'127.0.0.1' IDENTIFIED BY 'nueva-clave';
```

Para verlo en **MySQL Workbench** (diagrama ER para el informe): *Database → Reverse Engineer* sobre `genx_portal`.

## 3. Conectar la app

En el `.env` de cada servidor:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=genx_portal
DB_USER=genx_app
DB_PASSWORD=la-contraseña-del-paso-2
```

Comprobar y crear el administrador:

```bash
flask --app run check-db
```

```bash
flask --app run create-user admin --role admin
```

Los usuarios no se insertan a mano en SQL porque la contraseña se guarda con hash; `create-user` hace el `INSERT` a través del script de conexión.

## 4. Cómo encaja con la arquitectura DR

```text
                 IP virtual 10.0.0.10 (keepalived)
                          │
        ┌─────────────────┴─────────────────┐
  srv-activo (MASTER)                 srv-pasivo (BACKUP)
  ├─ App GenX   ▶ corriendo           ├─ App GenX   ■ detenida
  ├─ MySQL      ▶ corriendo           ├─ MySQL      ■ detenido
  └─ /srv/data (DRBD Primary) ══════▶ └─ DRBD Secondary
```

1. **MySQL no arranca solo** en ninguno de los dos servidores; lo controla keepalived:

```bash
sudo systemctl disable --now mysql
```

2. **Datos sobre DRBD.** Con DRBD como Primary y montado en `/srv/data`, en el activo:

```bash
sudo rsync -a /var/lib/mysql/ /srv/data/mysql/
```

   En **ambos** servidores:
   - En `/etc/mysql/mysql.conf.d/mysqld.cnf`, pon `datadir = /srv/data/mysql`.
   - Autoriza la nueva ruta en AppArmor: agrega `alias /var/lib/mysql/ -> /srv/data/mysql/,` al final de `/etc/apparmor.d/tunables/alias` y ejecuta `sudo systemctl reload apparmor`. Si no lo haces, MySQL no arranca y el error aparece como "permission denied".

3. **Scripts de keepalived:**
   - `notify_master`: `drbdadm primary r0` → `mount /dev/drbd0 /srv/data` → `systemctl start mysql` → arrancar la app.
   - `notify_backup`: detener la app → `systemctl stop mysql` → `umount /srv/data` → `drbdadm secondary r0`.

4. **Health check** para que keepalived detecte si la app o MySQL fallan:

```conf
vrrp_script chk_genx {
    script "/usr/bin/curl -fs http://127.0.0.1:5000/health"
    interval 3
    fall 2
}
```

5. **Respaldo lógico con cron** (además de DRBD), por ejemplo diario a las 2:00:

```cron
0 2 * * * mysqldump --single-transaction genx_portal | gzip > /backup/genx_$(date +\%F).sql.gz
```

   Luego sincronízalo con rsync hacia otro destino.

6. **ufw:** MySQL escucha solo en `127.0.0.1` (valor por defecto de Ubuntu), así que el puerto 3306 **no** se abre. Abre únicamente el puerto de DRBD (7789) entre los dos servidores y el de la app hacia la red del cliente.

## Errores a evitar

- **Que MySQL corra en los dos servidores a la vez sobre DRBD:** se corrompen los datos.
- **Hacer rsync de `/var/lib/mysql` con MySQL encendido:** la copia queda dañada. Para replicar la base se usa DRBD, y rsync se usa para los archivos de `mysqldump`.
- **Usar `utf8` en vez de `utf8mb4`:** los scripts ya usan `utf8mb4`.
