-- =====================================================================
-- Migración 005: Agregar columna es_complemento a tabla categoria
-- Fase 3.5: Carta y pedido en celular ("Complementa tu pedido")
-- Es idempotente: se puede correr múltiples veces sin error.
-- =====================================================================

ALTER TABLE categoria
  ADD COLUMN IF NOT EXISTS es_complemento BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN categoria.es_complemento IS 'Indica si la categoría es sugerida como complemento al armar un pedido (ej. bebidas, guarniciones, postres)';
