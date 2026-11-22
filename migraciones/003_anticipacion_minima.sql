-- Migración 003: Anticipación mínima para reservas web (Fase 3.3)
-- Permite definir cuántos minutos de anticipación exige el local antes de permitir una reserva web.

ALTER TABLE config_local
ADD COLUMN IF NOT EXISTS anticipacion_min_min SMALLINT NOT NULL DEFAULT 30 CHECK (anticipacion_min_min >= 0);
