-- =====================================================================
-- Quero APP – Esquema PostgreSQL v3 (MVP: reservas y pedidos)
-- Fuente de verdad del modelo de datos. Se ejecuta de arriba a abajo
-- (el orden respeta las llaves foráneas).
-- Escalable: lo que no entra en el MVP (mesas físicas, ingresos y egresos,
-- trabajadores, bitácora, cuentas de cliente) se agrega después SIN
-- modificar estas tablas.
--
-- CAMBIOS v3 respecto a v2:
--  * plato: nuevo codigo (número corto único y opcional para buscar el plato). Los platos con
--    dos precios se registran como dos platos (una variante por precio).
--  * config_local: nuevo max_reservas_web_por_telefono (tope de reservas web por teléfono en 24 h).
--  * v_cliente_actividad_24h: pedidos y reservas recientes del cliente (se calcula, no se guarda).
--  * El contacto NO se verifica con códigos: el teléfono es obligatorio y único, el correo es
--    opcional. Los abusos se frenan con la aceptación del staff, el pago antes de cocinar y el tope.
--
-- CAMBIOS v2 respecto a v1:
--  * cliente: se elimina "documento" (dato personal sin uso en el MVP).
--             El teléfono sigue siendo la identidad (obligatorio, único).
--  * config_local: nuevo umbral_alerta_pct (aviso "a punto de superar").
--  * reserva: nuevo excede_cupo (el staff puede forzar; la web NO).
--  * fn_carga_dia: devuelve la columna "nivel" (ok / alerta / excedido).
--  * tolerancia: es solo una referencia para alertar; el staff decide.
-- =====================================================================

-- ---------- Personal (usuarios con login) ----------
CREATE TABLE personal (
  personal_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre              VARCHAR(100) NOT NULL,
  correo              VARCHAR(120) NOT NULL,
  password_hash       VARCHAR(255) NOT NULL,
  rol                 VARCHAR(10)  NOT NULL CHECK (rol IN ('admin','empleado')),
  activo              BOOLEAN      NOT NULL DEFAULT TRUE,
  debe_cambiar_clave  BOOLEAN      NOT NULL DEFAULT TRUE,
  creado_en           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_personal_correo ON personal (lower(correo));

-- ---------- Configuración del local (una sola fila) ----------
-- Todo lo que la dueña ajusta vive aquí, no en el código.
CREATE TABLE config_local (
  config_id              SMALLINT PRIMARY KEY DEFAULT 1 CHECK (config_id = 1),
  nombre_local           VARCHAR(100) NOT NULL,
  aforo_personas         INT NOT NULL CHECK (aforo_personas > 0),
  total_mesas            INT NOT NULL CHECK (total_mesas > 0),
  personas_por_mesa      INT NOT NULL CHECK (personas_por_mesa > 0),
  duracion_estadia_min   INT NOT NULL CHECK (duracion_estadia_min > 0),
  franja_min             INT NOT NULL DEFAULT 30 CHECK (franja_min IN (15,30,60)),
  tolerancia_min         INT NOT NULL CHECK (tolerancia_min >= 0),   -- solo referencia: pasado este tiempo la app ALERTA; el staff decide si libera o reprograma
  umbral_preparacion_min INT NOT NULL CHECK (umbral_preparacion_min > 0),   -- cocina: pasado este tiempo el pedido se resalta en rojo
  max_reservas_web_por_telefono SMALLINT NOT NULL DEFAULT 2 CHECK (max_reservas_web_por_telefono >= 1), -- tope de reservas pedidas por la web con el mismo teléfono en 24 h (el staff no tiene tope)
  umbral_alerta_pct      SMALLINT NOT NULL DEFAULT 80 CHECK (umbral_alerta_pct BETWEEN 1 AND 100), -- a partir de este % de ocupación la franja se marca "alerta"
  hora_apertura          TIME NOT NULL,
  hora_cierre            TIME NOT NULL,
  dias_max_anticipacion  INT NOT NULL CHECK (dias_max_anticipacion >= 0),
  porcentaje_reservable  SMALLINT NULL CHECK (porcentaje_reservable BETWEEN 1 AND 100), -- NULL = 100 %
  abierto                BOOLEAN NOT NULL DEFAULT TRUE,
  yape_numero            VARCHAR(15)  NULL,
  yape_titular           VARCHAR(100) NULL,
  mensaje_pago           VARCHAR(300) NULL,
  CONSTRAINT ck_config_horario CHECK (hora_cierre > hora_apertura)
);

-- ---------- Cliente ----------
-- Se identifica por teléfono (9 dígitos, Perú). Se reutiliza si vuelve a pedir/reservar.
-- Sin cuenta ni contraseña (cliente "invitado"). El teléfono NO se verifica por código:
-- el staff lo comprueba al escribirle por WhatsApp antes de confirmar.
-- El correo es opcional y NO es único: una familia puede compartirlo, y fusionar fichas
-- por un dato es peor que tener un duplicado.
CREATE TABLE cliente (
  cliente_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre           VARCHAR(100) NOT NULL,
  telefono         VARCHAR(9)   NOT NULL UNIQUE CHECK (telefono ~ '^9[0-9]{8}$'),
  correo           VARCHAR(120) NULL,
  acepta_datos     BOOLEAN      NOT NULL CHECK (acepta_datos),     -- debe ser TRUE
  acepta_datos_en  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_cliente_correo ON cliente (lower(correo)) WHERE correo IS NOT NULL;

-- ---------- Carta ----------
CREATE TABLE categoria (
  categoria_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre        VARCHAR(50) NOT NULL UNIQUE,
  orden         SMALLINT    NOT NULL DEFAULT 0,
  activa        BOOLEAN     NOT NULL DEFAULT TRUE
);

-- Un plato con dos precios (personal / fuente, 1 L / 1½ L) se registra como DOS platos,
-- uno por tamaño, cada uno con su precio y su código. Los sabores sin cambio de precio
-- van en la nota del pedido, no como platos distintos.
CREATE TABLE plato (
  plato_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  categoria_id  INT NOT NULL REFERENCES categoria (categoria_id),
  codigo        INT NULL UNIQUE CHECK (codigo > 0),   -- número corto para buscar el plato (lo define la dueña; no es el ID)
  nombre        VARCHAR(100) NOT NULL,
  descripcion   VARCHAR(300) NULL,
  precio        NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
  disponible    BOOLEAN NOT NULL DEFAULT TRUE,   -- interruptor "plato agotado"
  activo        BOOLEAN NOT NULL DEFAULT TRUE    -- en lugar de borrar platos ya vendidos
);

-- ---------- Reserva ----------
CREATE TABLE reserva (
  reserva_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo             VARCHAR(12) NOT NULL UNIQUE,                        -- lo genera la app
  token              UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),     -- enlace del cliente
  cliente_id         INT  NOT NULL REFERENCES cliente (cliente_id),
  fecha              DATE NOT NULL,
  hora               TIME NOT NULL,
  hora_anterior      TIME NULL,                                          -- se llena al cambiar la hora (guarda solo el último cambio)
  cantidad_personas  INT  NOT NULL CHECK (cantidad_personas > 0),
  estado             VARCHAR(12) NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente','confirmada','rechazada','cancelada','llego','no_llego')),
  canal              VARCHAR(5)  NOT NULL DEFAULT 'staff' CHECK (canal IN ('web','staff')),
  excede_cupo        BOOLEAN NOT NULL DEFAULT FALSE,                     -- el staff confirmó/creó la reserva aun superando el cupo
  nota               VARCHAR(300) NULL,
  motivo             VARCHAR(200) NULL,                                  -- rechazo o cancelación
  creado_por         INT NULL REFERENCES personal (personal_id),         -- vacío si vino de la web
  creado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- La web nunca fuerza cupo: solo el staff puede excederlo.
  CONSTRAINT ck_reserva_forzar_solo_staff CHECK (NOT (excede_cupo AND canal = 'web' AND creado_por IS NULL AND estado = 'pendiente'))
);
CREATE INDEX ix_reserva_fecha_hora ON reserva (fecha, hora);
-- Un cliente no puede tener dos reservas activas a la misma fecha y hora
CREATE UNIQUE INDEX ux_reserva_cliente_fecha_hora
  ON reserva (cliente_id, fecha, hora)
  WHERE estado IN ('pendiente','confirmada','llego');

-- ---------- Pedido ----------
-- Los pedidos NO se limitan por aforo ni mesas.
CREATE TABLE pedido (
  pedido_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  token            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),       -- seguimiento del cliente
  cliente_id       INT NULL REFERENCES cliente (cliente_id),
  reserva_id       INT NULL REFERENCES reserva (reserva_id),             -- vacío = walk-in
  tipo             VARCHAR(6) NOT NULL CHECK (tipo IN ('local','recojo')),
  canal            VARCHAR(5) NOT NULL DEFAULT 'staff' CHECK (canal IN ('web','staff')),
  estado           VARCHAR(14) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','aceptado','en_preparacion','listo','entregado','rechazado','cancelado')),
  mesa_referencia  VARCHAR(20) NULL,           -- texto libre mientras no exista tabla de mesas
  nota             VARCHAR(300) NULL,
  motivo_rechazo   VARCHAR(200) NULL,
  creado_por       INT NULL REFERENCES personal (personal_id),
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  aceptado_en      TIMESTAMPTZ NULL,
  preparacion_en   TIMESTAMPTZ NULL,        -- cuándo entró a cocina (base del temporizador)
  listo_en         TIMESTAMPTZ NULL,
  entregado_en     TIMESTAMPTZ NULL,
  -- El pedido de recojo exige cliente (hay que avisarle); el pedido en local puede ser anónimo.
  CONSTRAINT ck_pedido_cliente CHECK (tipo = 'local' OR cliente_id IS NOT NULL)
);
CREATE INDEX ix_pedido_estado ON pedido (estado, creado_en);

CREATE TABLE detalle_pedido (
  detalle_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pedido_id     INT NOT NULL REFERENCES pedido (pedido_id) ON DELETE CASCADE,
  plato_id      INT NOT NULL REFERENCES plato (plato_id),
  cantidad      INT NOT NULL CHECK (cantidad > 0),
  precio_venta  NUMERIC(10,2) NOT NULL CHECK (precio_venta >= 0),  -- precio al momento del pedido
  nota          VARCHAR(200) NULL
);
CREATE INDEX ix_detalle_pedido ON detalle_pedido (pedido_id);

-- ---------- Pago (punto de enlace futuro con ingresos y egresos) ----------
CREATE TABLE pago (
  pago_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pedido_id       INT NOT NULL REFERENCES pedido (pedido_id),
  monto           NUMERIC(10,2) NOT NULL CHECK (monto > 0),
  medio           VARCHAR(13) NOT NULL CHECK (medio IN ('efectivo','yape','plin','transferencia','otro')),
  referencia      VARCHAR(60) NULL,                                -- n.º de operación
  confirmado_por  INT NOT NULL REFERENCES personal (personal_id),
  confirmado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_pago_pedido ON pago (pedido_id);

-- ---------- Registro de notificaciones (correo hoy, WhatsApp automático mañana) ----------
CREATE TABLE notificacion (
  notificacion_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tipo             VARCHAR(30) NOT NULL,   -- ej. reserva_confirmada, pedido_aceptado, pedido_listo
  canal            VARCHAR(10) NOT NULL CHECK (canal IN ('correo','whatsapp')),
  destino          VARCHAR(120) NOT NULL,
  reserva_id       INT NULL REFERENCES reserva (reserva_id),
  pedido_id        INT NULL REFERENCES pedido (pedido_id),
  estado           VARCHAR(10) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','enviada','fallida','manual')),  -- manual = staff abrió el enlace de WhatsApp
  error            VARCHAR(300) NULL,
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  enviada_en       TIMESTAMPTZ NULL,
  CONSTRAINT ck_notif_un_origen CHECK (num_nonnulls(reserva_id, pedido_id) = 1)
);
CREATE INDEX ix_notificacion_estado ON notificacion (estado, creado_en);

-- =====================================================================
-- Vistas y funciones: lo calculado NO se guarda
-- =====================================================================

-- Total, pagado y si está cobrado
CREATE VIEW v_pedido_resumen AS
SELECT p.pedido_id, p.tipo, p.estado, p.creado_en,
       COALESCE(d.total, 0)  AS total,
       COALESCE(g.pagado, 0) AS pagado,
       (COALESCE(d.total, 0) > 0 AND COALESCE(g.pagado, 0) >= COALESCE(d.total, 0)) AS cobrado
FROM pedido p
LEFT JOIN (SELECT pedido_id, SUM(cantidad * precio_venta) AS total
           FROM detalle_pedido GROUP BY pedido_id) d ON d.pedido_id = p.pedido_id
LEFT JOIN (SELECT pedido_id, SUM(monto) AS pagado
           FROM pago GROUP BY pedido_id) g ON g.pedido_id = p.pedido_id;

-- Actividad reciente del cliente (últimas 24 h). Sirve para avisar al staff de pedidos o
-- reservas repetidas. Los rechazados y cancelados no cuentan (un reintento legítimo no es abuso).
CREATE VIEW v_cliente_actividad_24h AS
SELECT c.cliente_id,
       (SELECT count(*) FROM pedido p
         WHERE p.cliente_id = c.cliente_id
           AND p.estado NOT IN ('rechazado','cancelado')
           AND p.creado_en > now() - interval '24 hours')  AS pedidos_24h,
       (SELECT count(*) FROM reserva r
         WHERE r.cliente_id = c.cliente_id
           AND r.estado NOT IN ('rechazada','cancelada')
           AND r.creado_en > now() - interval '24 hours')  AS reservas_24h,
       (SELECT count(*) FROM reserva r
         WHERE r.cliente_id = c.cliente_id
           AND r.canal = 'web'
           AND r.estado NOT IN ('rechazada','cancelada')
           AND r.creado_en > now() - interval '24 hours')  AS reservas_web_24h   -- se compara con config_local.max_reservas_web_por_telefono
FROM cliente c;

-- Carga de reservas por franja para un día (pizarra digital).
-- Cuenta solo reservas 'confirmada' y 'llego' (las pendientes NO reducen capacidad;
-- 'no_llego', 'cancelada' y 'rechazada' liberan el cupo).
-- Una reserva ocupa mesa durante toda su estadía, por eso aparece en cada franja que cubre.
-- Mesas requeridas por reserva = personas / personas_por_mesa, redondeado hacia arriba.
-- "nivel" alimenta las alertas del staff (el staff NO queda bloqueado):
--   'ok'       = por debajo del umbral de alerta
--   'alerta'   = ocupación >= umbral_alerta_pct (a punto de superar)
--   'excedido' = se superó el límite de personas o de mesas (mostrar en rojo)
-- personas_libres / mesas_libres pueden salir NEGATIVAS cuando hay exceso.
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
           (r.fecha + r.hora) + make_interval(mins => c.duracion_estadia_min) AS fin,
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

-- ¿Cabe un grupo nuevo (o una reserva movida) en TODAS las franjas que ocuparía?
-- Fuera del horario del local devuelve FALSE.
-- USO: la WEB la usa como filtro duro (el cliente no ve el salón).
--      El STAFF la usa solo para decidir si muestra la alerta y marca
--      reserva.excede_cupo = TRUE cuando fuerza; nunca queda bloqueado.
CREATE OR REPLACE FUNCTION fn_hay_cupo(p_fecha DATE, p_hora TIME, p_personas INT,
                                       p_excluir_reserva INT DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(bool_and(
           f.personas + p_personas <= f.limite_personas
       AND f.mesas + CEIL(p_personas::numeric / c.personas_por_mesa)::INT <= f.limite_mesas), FALSE)
  FROM fn_carga_dia(p_fecha, p_excluir_reserva) f, config_local c
  WHERE c.config_id = 1
    AND (p_fecha + f.franja_inicio) < (p_fecha + p_hora) + make_interval(mins => c.duracion_estadia_min)
    AND (p_fecha + f.franja_fin)    > (p_fecha + p_hora);
$$;
