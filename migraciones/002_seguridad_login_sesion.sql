-- =====================================================================
-- Fase S1 · 002: seguridad de login y sesión
-- 1. personal.sesion_version para invalidar sesiones al hacer logout o cambiar clave.
-- 2. intento_login para registrar intentos y mitigar fuerza bruta (bloqueo temporal).
-- Repetible: puede correrse varias veces sin error.
-- =====================================================================
BEGIN;

-- 1. sesion_version en personal
ALTER TABLE personal
  ADD COLUMN IF NOT EXISTS sesion_version INT NOT NULL DEFAULT 1;

-- 2. Tabla intento_login
CREATE TABLE IF NOT EXISTS intento_login (
  intento_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  correo_lower  VARCHAR(255) NOT NULL,
  ip            VARCHAR(45)  NOT NULL,
  exitoso       BOOLEAN      NOT NULL DEFAULT FALSE,
  creado_en     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_intento_login_correo_tiempo ON intento_login (correo_lower, creado_en);
CREATE INDEX IF NOT EXISTS idx_intento_login_ip_tiempo ON intento_login (ip, creado_en);

COMMIT;
