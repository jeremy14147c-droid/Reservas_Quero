-- =====================================================================
-- DATOS DE EJEMPLO PARA DESARROLLO. Reemplazar por los reales de la dueña.
-- (Los usuarios de personal se crean con el comando de la app, porque la
--  contraseña debe guardarse con el hash de Flask.)
-- =====================================================================
INSERT INTO config_local
  (nombre_local, aforo_personas, total_mesas, personas_por_mesa, duracion_estadia_min,
   franja_min, tolerancia_min, umbral_preparacion_min, hora_apertura, hora_cierre, dias_max_anticipacion,
   porcentaje_reservable, abierto)
VALUES ('Pollería (nombre de ejemplo)', 40, 10, 4, 90, 30, 15, 20, '12:00', '22:00', 2, NULL, TRUE);

INSERT INTO categoria (nombre, orden) VALUES ('Platos de fondo', 1), ('Alitas', 2), ('Bebidas', 3);

INSERT INTO plato (categoria_id, nombre, precio) VALUES
  (1, 'Lomo saltado (ejemplo)', 25.00),
  (2, 'Alitas BBQ x9 (ejemplo)', 20.00),
  (3, 'Gaseosa personal (ejemplo)', 4.00);
