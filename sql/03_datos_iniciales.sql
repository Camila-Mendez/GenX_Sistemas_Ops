-- =========================================================
-- GenX · 03 — Datos iniciales (catálogo de planes)
-- Ejecutar en la VM (servidor activo) como root:
--     sudo mysql < sql/03_datos_iniciales.sql
-- Se puede ejecutar varias veces: actualiza los planes existentes.
-- =========================================================

USE genx_portal;

INSERT INTO planes (slug, name, description, rto, rpo, price_monthly) VALUES
  ('respaldo-programado', 'Respaldo Programado',
   'Copias incrementales con rsync y cron hacia el servidor pasivo, con retención de 30 días y reporte diario.',
   '4 horas', '24 horas', 45.00),
  ('replicacion-drbd', 'Replicación en Tiempo Real',
   'Bloque de almacenamiento replicado con DRBD (protocolo C) entre nodo activo y pasivo. Cero pérdida de datos confirmados.',
   '30 minutos', '≈ 0', 120.00),
  ('alta-disponibilidad', 'Alta Disponibilidad',
   'DRBD + keepalived con IP virtual (VRRP). El nodo pasivo toma el control automáticamente si el activo deja de responder.',
   '< 1 minuto', '≈ 0', 210.00),
  ('hardening', 'Seguridad y Hardening',
   'Reglas ufw, fail2ban, SSH solo por llave y auditoría de accesos en ambos servidores Ubuntu.',
   'N/A', 'N/A', 60.00)
AS nuevo
ON DUPLICATE KEY UPDATE
  name = nuevo.name,
  description = nuevo.description,
  rto = nuevo.rto,
  rpo = nuevo.rpo,
  price_monthly = nuevo.price_monthly;

-- Los usuarios NO se insertan aquí porque la contraseña debe guardarse con hash.
-- Crea el administrador desde la app con:
--     flask --app run create-user admin --role admin
