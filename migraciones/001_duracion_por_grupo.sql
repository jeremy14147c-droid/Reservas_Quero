-- =====================================================================
-- Fase 3.2 · 001: duración de estadía por tamaño del grupo
-- Cada reserva ocupa mesa un tiempo que depende de sus personas:
--   1 a 3 personas  -> duracion_1_3_min   (30 min por defecto)
--   4 a 7 personas  -> duracion_4_7_min   (60 min por defecto)
--   8 o más         -> duracion_8_mas_min (90 min por defecto)
-- Los valores por defecto son los que valen (decisión de la dueña); NO se
-- copia el valor viejo de duracion_estadia_min para no heredar valores raros.
-- Repetible: puede correrse varias veces sin error y cambia solo lo que falta.
-- Aplicar:  psql -f migraciones/001_duracion_por_grupo.sql  (con la conexión del .env)
-- =====================================================================
BEGIN;

-- a) Columnas nuevas en config_local (IF NOT EXISTS permite correrlo otra vez)
ALTER TABLE config_local
  ADD COLUMN IF NOT EXISTS duracion_1_3_min  INT NOT NULL DEFAULT 30 CHECK (duracion_1_3_min  > 0),
  ADD COLUMN IF NOT EXISTS duracion_4_7_min  INT NOT NULL DEFAULT 60 CHECK (duracion_4_7_min  > 0),
  ADD COLUMN IF NOT EXISTS duracion_8_mas_min INT NOT NULL DEFAULT 90 CHECK (duracion_8_mas_min > 0);

-- b) Única fuente de verdad de la duración: función SQL
CREATE OR REPLACE FUNCTION fn_duracion_estadia(p_personas INT)
RETURNS INT STABLE AS $$
  SELECT CASE
           WHEN p_personas <= 3 THEN c.duracion_1_3_min      -- grupos de 1 a 3
           WHEN p_personas <= 7 THEN c.duracion_4_7_min      -- grupos de 4 a 7
           ELSE c.duracion_8_mas_min                          -- 8 en adelante
         END
  FROM config_local c WHERE c.config_id = 1;
$$ LANGUAGE sql;

-- c) Reemplazo de fn_carga_dia: la duración de CADA reserva sale de fn_duracion_estadia
--    (misma lógica que schema.sql; solo cambia cómo se calcula la hora de fin).
CREATE OR REPLACE FUNCTION fn_carga_dia(p_fecha DATE, p_excluir_reserva INT DEFAULT NULL)
RETURNS TABLE (
  franja_inicio TIME, franja_fin TIME,
  reservas INT, personas INT, mesas INT,
  limite_personas INT, limite_mesas INT,
  personas_libres INT, mesas_libres INT,
  limita TEXT,
  nivel TEXT
)
LANGUAGE sql STABLE AS $$
  WITH c AS (SELECT * FROM config_local WHERE config_id = 1),
  bloques AS (
    SELECT gs AS b_ini, gs + make_interval(mins => c.franja_min) AS b_fin
    FROM c,
         generate_series(p_fecha + c.hora_apertura,
                         p_fecha + c.hora_cierre - make_interval(mins => c.franja_min),
                         make_interval(mins => c.franja_min)) gs
  ),
  activas AS (
    SELECT r.reserva_id, r.cantidad_personas,
           (r.fecha + r.hora) AS ini,
           (r.fecha + r.hora) + make_interval(mins => fn_duracion_estadia(r.cantidad_personas)) AS fin,
           CEIL(r.cantidad_personas::numeric / c.personas_por_mesa)::INT AS mesas_req
    FROM reserva r, c
    WHERE r.fecha = p_fecha
      AND r.estado IN ('confirmada','llego')
      AND r.reserva_id IS DISTINCT FROM p_excluir_reserva
  ),
  carga AS (
    SELECT b.b_ini, b.b_fin,
           COUNT(a.reserva_id)::INT                 AS reservas,
           COALESCE(SUM(a.cantidad_personas), 0)::INT AS personas,
           COALESCE(SUM(a.mesas_req), 0)::INT         AS mesas
    FROM bloques b
    LEFT JOIN activas a ON a.ini < b.b_fin AND a.fin > b.b_ini
    GROUP BY b.b_ini, b.b_fin
  )
  SELECT k.b_ini::TIME, k.b_fin::TIME, k.reservas, k.personas, k.mesas,
         lim.lp, lim.lm,
         lim.lp - k.personas,
         lim.lm - k.mesas,
         CASE WHEN (lim.lm - k.mesas) * c.personas_por_mesa < (lim.lp - k.personas)
              THEN 'mesas' ELSE 'personas' END,
         CASE WHEN k.personas > lim.lp OR k.mesas > lim.lm THEN 'excedido'
              WHEN GREATEST(k.personas::numeric / NULLIF(lim.lp, 0),
                            k.mesas::numeric    / NULLIF(lim.lm, 0)) * 100 >= c.umbral_alerta_pct
              THEN 'alerta'
              ELSE 'ok' END
  FROM carga k
  CROSS JOIN c
  CROSS JOIN LATERAL (
    SELECT FLOOR(c.aforo_personas * COALESCE(c.porcentaje_reservable, 100) / 100.0)::INT AS lp,
           FLOOR(c.total_mesas    * COALESCE(c.porcentaje_reservable, 100) / 100.0)::INT AS lm
  ) lim
  ORDER BY k.b_ini;
$$;

-- d) Reemplazo de fn_hay_cupo: el grupo nuevo debe caber en TODAS las franjas
--    que ocupa DURANTE SU DURACIÓN (hora + fn_duracion_estadia(p_personas)).
CREATE OR REPLACE FUNCTION fn_hay_cupo(p_fecha DATE, p_hora TIME, p_personas INT,
                                       p_excluir_reserva INT DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(bool_and(
           f.personas + p_personas <= f.limite_personas
       AND f.mesas + CEIL(p_personas::numeric / c.personas_por_mesa)::INT <= f.limite_mesas), FALSE)
  FROM fn_carga_dia(p_fecha, p_excluir_reserva) f, config_local c
  WHERE c.config_id = 1
    AND (p_fecha + f.franja_inicio) < (p_fecha + p_hora) + make_interval(mins => fn_duracion_estadia(p_personas))
    AND (p_fecha + f.franja_fin)    > (p_fecha + p_hora);
$$;

-- e) Ya nadie usa la columna vieja: fuera (recién después de reemplazar las funciones)
ALTER TABLE config_local DROP COLUMN IF EXISTS duracion_estadia_min;

COMMIT;
