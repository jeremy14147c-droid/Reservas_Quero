-- 1. Tablas
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

CREATE TABLE config_local (
  config_id              SMALLINT PRIMARY KEY DEFAULT 1 CHECK (config_id = 1),
  nombre_local           VARCHAR(100) NOT NULL,
  aforo_personas         INT NOT NULL CHECK (aforo_personas > 0),
  total_mesas            INT NOT NULL CHECK (total_mesas > 0),
  personas_por_mesa      INT NOT NULL CHECK (personas_por_mesa > 0),
  duracion_estadia_min   INT NOT NULL CHECK (duracion_estadia_min > 0),
  franja_min             INT NOT NULL DEFAULT 30 CHECK (franja_min IN (15,30,60)),
  tolerancia_min         INT NOT NULL CHECK (tolerancia_min >= 0),
  umbral_preparacion_min INT NOT NULL CHECK (umbral_preparacion_min > 0),
  max_reservas_web_por_telefono SMALLINT NOT NULL DEFAULT 2 CHECK (max_reservas_web_por_telefono >= 1),
  umbral_alerta_pct      SMALLINT NOT NULL DEFAULT 80 CHECK (umbral_alerta_pct BETWEEN 1 AND 100),
  hora_apertura          TIME NOT NULL,
  hora_cierre            TIME NOT NULL,
  dias_max_anticipacion  INT NOT NULL CHECK (dias_max_anticipacion >= 0),
  porcentaje_reservable  SMALLINT NULL CHECK (porcentaje_reservable BETWEEN 1 AND 100),
  abierto                BOOLEAN NOT NULL DEFAULT TRUE,
  yape_numero            VARCHAR(15)  NULL,
  yape_titular           VARCHAR(100) NULL,
  mensaje_pago           VARCHAR(300) NULL,
  CONSTRAINT ck_config_horario CHECK (hora_cierre > hora_apertura)
);

CREATE TABLE cliente (
  cliente_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre           VARCHAR(100) NOT NULL,
  telefono         VARCHAR(9)   NOT NULL UNIQUE CHECK (telefono ~ '^9[0-9]{8}$'),
  correo           VARCHAR(120) NULL,
  acepta_datos     BOOLEAN      NOT NULL CHECK (acepta_datos),
  acepta_datos_en  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_cliente_correo ON cliente (lower(correo)) WHERE correo IS NOT NULL;

CREATE TABLE categoria (
  categoria_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre        VARCHAR(50) NOT NULL UNIQUE,
  orden         SMALLINT    NOT NULL DEFAULT 0,
  activa        BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE plato (
  plato_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  categoria_id  INT NOT NULL REFERENCES categoria (categoria_id),
  nombre        VARCHAR(100) NOT NULL,
  descripcion   VARCHAR(300) NULL,
  precio        NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
  disponible    BOOLEAN NOT NULL DEFAULT TRUE,
  activo        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE reserva (
  reserva_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo             VARCHAR(12) NOT NULL UNIQUE,
  token              UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  cliente_id         INT  NOT NULL REFERENCES cliente (cliente_id),
  fecha              DATE NOT NULL,
  hora               TIME NOT NULL,
  hora_anterior      TIME NULL,
  cantidad_personas  INT  NOT NULL CHECK (cantidad_personas > 0),
  estado             VARCHAR(12) NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente','confirmada','rechazada','cancelada','llego','no_llego')),
  canal              VARCHAR(5)  NOT NULL DEFAULT 'staff' CHECK (canal IN ('web','staff')),
  excede_cupo        BOOLEAN NOT NULL DEFAULT FALSE,
  nota               VARCHAR(300) NULL,
  motivo             VARCHAR(200) NULL,
  creado_por         INT NULL REFERENCES personal (personal_id),
  creado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_reserva_forzar_solo_staff CHECK (NOT (excede_cupo AND canal = 'web' AND creado_por IS NULL AND estado = 'pendiente'))
);
CREATE INDEX ix_reserva_fecha_hora ON reserva (fecha, hora);
CREATE UNIQUE INDEX ux_reserva_cliente_fecha_hora
  ON reserva (cliente_id, fecha, hora)
  WHERE estado IN ('pendiente','confirmada','llego');

CREATE TABLE pedido (
  pedido_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  token            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  cliente_id       INT NULL REFERENCES cliente (cliente_id),
  reserva_id       INT NULL REFERENCES reserva (reserva_id),
  tipo             VARCHAR(6) NOT NULL CHECK (tipo IN ('local','recojo')),
  canal            VARCHAR(5) NOT NULL DEFAULT 'staff' CHECK (canal IN ('web','staff')),
  estado           VARCHAR(14) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','aceptado','en_preparacion','listo','entregado','rechazado','cancelado')),
  mesa_referencia  VARCHAR(20) NULL,
  nota             VARCHAR(300) NULL,
  motivo_rechazo   VARCHAR(200) NULL,
  creado_por       INT NULL REFERENCES personal (personal_id),
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  aceptado_en      TIMESTAMPTZ NULL,
  preparacion_en   TIMESTAMPTZ NULL,
  listo_en         TIMESTAMPTZ NULL,
  entregado_en     TIMESTAMPTZ NULL,
  CONSTRAINT ck_pedido_cliente CHECK (tipo = 'local' OR cliente_id IS NOT NULL)
);
CREATE INDEX ix_pedido_estado ON pedido (estado, creado_en);

CREATE TABLE detalle_pedido (
  detalle_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pedido_id     INT NOT NULL REFERENCES pedido (pedido_id) ON DELETE CASCADE,
  plato_id      INT NOT NULL REFERENCES plato (plato_id),
  cantidad      INT NOT NULL CHECK (cantidad > 0),
  precio_venta  NUMERIC(10,2) NOT NULL CHECK (precio_venta >= 0),
  nota          VARCHAR(200) NULL
);
CREATE INDEX ix_detalle_pedido ON detalle_pedido (pedido_id);

CREATE TABLE pago (
  pago_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pedido_id       INT NOT NULL REFERENCES pedido (pedido_id),
  monto           NUMERIC(10,2) NOT NULL CHECK (monto > 0),
  medio           VARCHAR(13) NOT NULL CHECK (medio IN ('efectivo','yape','plin','transferencia','otro')),
  referencia      VARCHAR(60) NULL,
  confirmado_por  INT NOT NULL REFERENCES personal (personal_id),
  confirmado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_pago_pedido ON pago (pedido_id);

CREATE TABLE notificacion (
  notificacion_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tipo             VARCHAR(30) NOT NULL,
  canal            VARCHAR(10) NOT NULL CHECK (canal IN ('correo','whatsapp')),
  destino          VARCHAR(120) NOT NULL,
  reserva_id       INT NULL REFERENCES reserva (reserva_id),
  pedido_id        INT NULL REFERENCES pedido (pedido_id),
  estado           VARCHAR(10) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','enviada','fallida','manual')),
  error            VARCHAR(300) NULL,
  creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
  enviada_en       TIMESTAMPTZ NULL,
  CONSTRAINT ck_notif_un_origen CHECK (num_nonnulls(reserva_id, pedido_id) = 1)
);
CREATE INDEX ix_notificacion_estado ON notificacion (estado, creado_en);

-- 2. Vistas y Funciones
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
           AND r.creado_en > now() - interval '24 hours')  AS reservas_web_24h
FROM cliente c;

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

-- 3. Cargar datos de Jhoana (Dueña)
INSERT INTO config_local (
  config_id, nombre_local, aforo_personas, total_mesas, personas_por_mesa,
  duracion_estadia_min, franja_min, tolerancia_min, umbral_preparacion_min,
  max_reservas_web_por_telefono, umbral_alerta_pct, hora_apertura, hora_cierre,
  dias_max_anticipacion, porcentaje_reservable, abierto, yape_numero, yape_titular, mensaje_pago
) VALUES (
  1, 'Quero', 60, 15, 4, 90, 30, 20, 20, 2, 80, '12:00:00', '22:00:00', 2, 100, true,
  '996908138', 'Jhoana', 'Enviar captura del Yape al 996908138'
);

-- 4. Personal de Quero
INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave)
VALUES 
  ('Jhoana Dueña', 'admin@quero.pe', 'admin123', 'admin', true, false),
  ('Luis Mozo', 'mozo@quero.pe', 'mozo123', 'empleado', true, false);

-- 5. Categorías y Carta
INSERT INTO categoria (nombre, orden, activa) VALUES
  ('Platos de Fondo', 1, true),
  ('Bebidas', 2, true);

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo) VALUES
  (1, 'Lomo Saltado', 'Con papas fritas y arroz criollo', 38.00, true, true),
  (1, 'Ceviche Clásico', 'Pescado fresco del día con camote y choclo', 35.00, true, true),
  (2, 'Chicha Morada 1L', 'Jarra artesanal de la casa', 15.00, true, true);

-- 6. Asignar todos los permisos a quero_app
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO quero_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO quero_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO quero_app;

-- 1. Asegurar categorías
INSERT INTO categoria (nombre, orden, activa) VALUES
  ('Entradas', 1, true),
  ('Platos de Fondo', 2, true),
  ('Postres', 3, true),
  ('Bebidas', 4, true)
ON CONFLICT (nombre) DO NOTHING;

-- 2. Platos variados y representativos
INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Causa Limeña de Pollo', 'Papas amarillas prensadas con ají amarillo y relleno de pollo deshilachado', 22.00, true, true
FROM categoria c WHERE c.nombre = 'Entradas'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Causa Limeña de Pollo');

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Tequeños con Guacamole', 'Rellenos de queso andino con salsa de palta', 18.00, true, true
FROM categoria c WHERE c.nombre = 'Entradas'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Tequeños con Guacamole');

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Ají de Gallina Clásico', 'Crema cremosa de ají amarillo con huevo, aceituna y arroz blanco', 32.00, true, true
FROM categoria c WHERE c.nombre = 'Platos de Fondo'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Ají de Gallina Clásico');

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Arroz con Mariscos', 'Flambeado con mariscos selectos, ají panca y queso parmesano', 42.00, true, true
FROM categoria c WHERE c.nombre = 'Platos de Fondo'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Arroz con Mariscos');

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Suspiro a la Limeña', 'Dulce tradicional con manjarblanco de yemas y merengue al oporto', 14.00, true, true
FROM categoria c WHERE c.nombre = 'Postres'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Suspiro a la Limeña');

INSERT INTO plato (categoria_id, nombre, descripcion, precio, disponible, activo)
SELECT c.categoria_id, 'Limonada Frozen 1L', 'Jarra refrescante con hierbabuena', 16.00, true, true
FROM categoria c WHERE c.nombre = 'Bebidas'
AND NOT EXISTS (SELECT 1 FROM plato WHERE nombre = 'Limonada Frozen 1L');


-- 1. VER LA CONFIGURACIÓN REAL DE JHOANA (Aforo 60, 15 mesas, Yape)
SELECT 
  nombre_local,
  aforo_personas,
  total_mesas,
  personas_por_mesa,
  duracion_estadia_min,
  hora_apertura,
  hora_cierre,
  dias_max_anticipacion,
  yape_numero,
  yape_titular
FROM config_local;


-- 2. VER EL CÁLCULO DE CUPOS Y SEMÁFORO EN TIEMPO REAL (Función fn_carga_dia)
-- Devuelve las 20 franjas horarias con mesas y personas libres
SELECT * FROM fn_carga_dia(CURRENT_DATE);


-- 3. VER LA CARTA COMPLETA CON PRECIOS Y DISPONIBILIDAD
SELECT 
  c.nombre AS categoria,
  p.nombre AS plato,
  p.precio,
  CASE WHEN p.disponible THEN 'Disponible' ELSE 'Agotado' END AS estado
FROM plato p
JOIN categoria c ON c.categoria_id = p.categoria_id
ORDER BY c.orden, p.nombre;


-- 4. VER LAS CUENTAS DEL PERSONAL Y SUS ROLES
SELECT 
  personal_id,
  nombre,
  correo,
  rol,
  activo,
  creado_en
FROM personal;


-- 5. VER LAS RESERVAS REGISTRADAS (Con datos del cliente)
SELECT 
  r.reserva_id,
  r.codigo,
  c.nombre AS cliente,
  c.telefono,
  r.fecha,
  r.hora,
  r.cantidad_personas AS personas,
  r.estado,
  r.canal,
  r.actualizado_en
FROM reserva r
JOIN cliente c ON c.cliente_id = r.cliente_id
ORDER BY r.creado_en DESC;


-- 6. VER LA ÚLTIMA RESERVA CREADA EN VIVO (Para probar en la exposición)
SELECT 
  r.codigo,
  c.nombre,
  r.fecha,
  r.hora,
  r.cantidad_personas,
  r.estado
FROM reserva r
JOIN cliente c ON c.cliente_id = r.cliente_id
ORDER BY r.creado_en DESC
LIMIT 1;


-- 7. VER LAS COMANDAS / PEDIDOS DE SALÓN (Con detalle de platos y subtotal)
SELECT 
  p.pedido_id,
  p.mesa_referencia AS mesa,
  p.estado,
  d.cantidad,
  pl.nombre AS plato,
  d.precio_venta,
  (d.cantidad * d.precio_venta) AS subtotal
FROM pedido p
JOIN detalle_pedido d ON d.pedido_id = p.pedido_id
JOIN plato pl ON pl.plato_id = d.plato_id
ORDER BY p.creado_en DESC;


-- 8. VER LOS COBROS REGISTRADOS (Yape / Plin / Efectivo)
SELECT 
  pago_id,
  pedido_id,
  monto,
  medio,
  referencia,
  confirmado_en
FROM pago
ORDER BY confirmado_en DESC;


-- 9. VISTA CALCULADA DE RESUMEN (Muestra si cada pedido está cobrado)
SELECT * FROM v_pedido_resumen ORDER BY creado_en DESC;
