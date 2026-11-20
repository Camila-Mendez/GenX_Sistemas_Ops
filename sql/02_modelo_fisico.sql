-- =========================================================
-- GenX · 02 — Modelo físico (tablas, llaves e índices)
-- Ejecutar en la VM (servidor activo) como root:
--     sudo mysql < sql/02_modelo_fisico.sql
-- =========================================================

USE genx_portal;

-- Usuarios del portal: 'admin' (panel de operaciones) o 'cliente' (portal de planes)
CREATE TABLE IF NOT EXISTS usuarios (
  id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  username       VARCHAR(50)   NOT NULL,
  email          VARCHAR(120)  NOT NULL,
  full_name      VARCHAR(120)  NOT NULL,
  company        VARCHAR(120)  NULL,
  password_hash  VARCHAR(255)  NOT NULL,
  role           ENUM('admin','cliente') NOT NULL DEFAULT 'cliente',
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login     DATETIME      NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_username (username),
  UNIQUE KEY uq_usuarios_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bitácora de inicios de sesión: guarda qué nodo (activo/pasivo) respondió
CREATE TABLE IF NOT EXISTS bitacora_login (
  id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  username    VARCHAR(50)   NOT NULL,
  success     BOOLEAN       NOT NULL,
  node        VARCHAR(100)  NOT NULL,
  ip_address  VARCHAR(45)   NULL,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_bitacora_login_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Catálogo de planes de recuperación ante desastres
CREATE TABLE IF NOT EXISTS planes (
  id             INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  slug           VARCHAR(50)    NOT NULL,
  name           VARCHAR(100)   NOT NULL,
  description    VARCHAR(500)   NOT NULL,
  rto            VARCHAR(30)    NOT NULL,   -- Recovery Time Objective
  rpo            VARCHAR(30)    NOT NULL,   -- Recovery Point Objective
  price_monthly  DECIMAL(10,2)  NOT NULL,   -- por servidor
  active         BOOLEAN        NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  UNIQUE KEY uq_planes_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Solicitudes de servicio (encabezado)
CREATE TABLE IF NOT EXISTS solicitudes (
  id             INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  user_id        INT UNSIGNED   NOT NULL,
  site           VARCHAR(120)   NOT NULL,
  contact_phone  VARCHAR(30)    NULL,
  notes          VARCHAR(1000)  NULL,
  status         ENUM('Recibida','En análisis','En implementación','Activa','Cancelada')
                                NOT NULL DEFAULT 'Recibida',
  total_monthly  DECIMAL(10,2)  NOT NULL,
  created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_solicitudes_user (user_id),
  CONSTRAINT fk_solicitudes_usuario FOREIGN KEY (user_id) REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Solicitudes de servicio (detalle: un plan por línea)
CREATE TABLE IF NOT EXISTS solicitud_detalle (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  request_id  INT UNSIGNED   NOT NULL,
  plan_id     INT UNSIGNED   NOT NULL,
  servers     INT UNSIGNED   NOT NULL,
  unit_price  DECIMAL(10,2)  NOT NULL,
  PRIMARY KEY (id),
  KEY ix_detalle_request (request_id),
  KEY ix_detalle_plan (plan_id),
  CONSTRAINT fk_detalle_solicitud FOREIGN KEY (request_id) REFERENCES solicitudes (id) ON DELETE CASCADE,
  CONSTRAINT fk_detalle_plan FOREIGN KEY (plan_id) REFERENCES planes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mensajes del formulario de contacto
CREATE TABLE IF NOT EXISTS mensajes_contacto (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  name        VARCHAR(120)   NOT NULL,
  email       VARCHAR(120)   NOT NULL,
  company     VARCHAR(120)   NULL,
  message     VARCHAR(2000)  NOT NULL,
  created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
