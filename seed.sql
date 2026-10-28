-- =====================================================================
-- DATOS INICIALES REALES: Quero Gastrobar (Lima, Perú)
-- Obtenidos de la carta oficial del restaurante.
-- Cara 1: Platos y comida (Ceviches, Chicharrones, Arroces, etc.)
-- Cara 2: Bebidas, cervezas y coctelería
-- =====================================================================
INSERT INTO config_local
  (config_id, nombre_local, aforo_personas, total_mesas, personas_por_mesa,
   duracion_1_3_min, duracion_4_7_min, duracion_8_mas_min,
   franja_min, tolerancia_min, umbral_preparacion_min, max_reservas_web_por_telefono, umbral_alerta_pct,
   hora_apertura, hora_cierre, dias_max_anticipacion, porcentaje_reservable, abierto,
   yape_numero, yape_titular, mensaje_pago)
VALUES
  (1, 'Quero Gastrobar', 48, 12, 4, 30, 60, 90, 30, 15, 20, 2, 80,
   '12:00', '23:00', 3, NULL, TRUE,
   '996908138', 'Quero Gastrobar', 'Envía tu comprobante de pago al WhatsApp 996908138 indicando tu código de pedido.')
ON CONFLICT (config_id) DO UPDATE SET
  nombre_local = EXCLUDED.nombre_local,
  yape_numero = EXCLUDED.yape_numero,
  yape_titular = EXCLUDED.yape_titular,
  mensaje_pago = EXCLUDED.mensaje_pago,
  hora_cierre = EXCLUDED.hora_cierre;
-- OJO: los parámetros operativos (aforo, mesas, duraciones...) solo se insertan si la fila no
-- existe; si ya existe NO se sobrescriben, para no borrar los ajustes hechos por la dueña.

-- 1. Categorías en orden oficial: primero comidas (Cara 1) y luego bebidas (Cara 2)
INSERT INTO categoria (nombre, orden, activa) VALUES
  ('Ceviches', 1, TRUE),
  ('Dúos y Tríos Marinos', 2, TRUE),
  ('Chicharrones y Jaleas', 3, TRUE),
  ('Arroces', 4, TRUE),
  ('Filetes y Pescados', 5, TRUE),
  ('Sopas', 6, TRUE),
  ('Platos Criollos y Fondos', 7, TRUE),
  ('Hamburguesas', 8, TRUE),
  ('Piqueos y Alitas', 9, TRUE),
  ('Tequeños', 10, TRUE),
  ('Guarniciones', 11, TRUE),
  ('Cócteles', 12, TRUE),
  ('Cervezas', 13, TRUE),
  ('Bebidas y Jugos', 14, TRUE),
  ('Bebidas Calientes', 15, TRUE)
ON CONFLICT (nombre) DO UPDATE SET orden = EXCLUDED.orden;

-- Limpiar platos anteriores de ejemplo si no tienen pedidos vinculados
DELETE FROM plato WHERE NOT EXISTS (SELECT 1 FROM detalle_pedido WHERE detalle_pedido.plato_id = plato.plato_id);

-- 2. Platos oficiales con códigos únicos y variantes de dos precios (Personal / Fuente)
INSERT INTO plato (categoria_id, codigo, nombre, precio, descripcion, disponible, activo)
SELECT c.categoria_id, p.codigo, p.nombre, p.precio, p.descripcion, TRUE, TRUE
FROM (VALUES
  -- CEVICHES (con variantes de precio Personal y Fuente)
  ('Ceviches', 1, 'Ceviche de Pescado — Personal', 15.00, 'Pescado fresco del día con cebolla, camote y choclo desgranado.'),
  ('Ceviches', 2, 'Ceviche de Pescado — Fuente', 25.00, 'Porción generosa para compartir de ceviche de pescado.'),
  ('Ceviches', 3, 'Ceviche Mixto — Personal', 20.00, 'Pescado y mixtura de mariscos marinados en zumo de limón fresco.'),
  ('Ceviches', 4, 'Ceviche Mixto — Fuente', 28.00, 'Fuente familiar de ceviche mixto con mariscos seleccionados.'),
  ('Ceviches', 5, 'Leche de Tigre — Vaso', 15.00, 'Concentrado de ceviche con trozos de pescado y canchita.'),
  ('Ceviches', 6, 'Leche de Tigre — Copa', 20.00, 'Presentación especial en copa con chicharrón de pota montado.'),
  ('Ceviches', 7, 'Ceviche de Pota', 15.00, 'Tiras de pota fresca con toque picante y crocante.'),

  -- DÚOS Y TRÍOS MARINOS
  ('Dúos y Tríos Marinos', 8, 'Dúo Marino — Personal', 22.00, 'Ceviche de pescado más chicharrón de pescado.'),
  ('Dúos y Tríos Marinos', 9, 'Dúo Marino — Fuente', 50.00, 'Fuente para compartir de ceviche y chicharrón mixto.'),
  ('Dúos y Tríos Marinos', 10, 'Trío Marino — Personal', 25.00, 'Ceviche, chicharrón de pescado y arroz con mariscos.'),
  ('Dúos y Tríos Marinos', 11, 'Trío Marino — Fuente', 60.00, 'Fuente completa con ceviche, chicharrón y arroz con mariscos.'),

  -- CHICHARRONES Y JALEAS
  ('Chicharrones y Jaleas', 12, 'Chicharrón de Pescado', 22.00, 'Trozos de pescado crocante con yuca dorada y tártara.'),
  ('Chicharrones y Jaleas', 13, 'Chicharrón Mixto', 25.00, 'Pescado y mariscos crujientes acompañados de sarza criolla.'),
  ('Chicharrones y Jaleas', 14, 'Chicharrón de Pota', 15.00, 'Aros de pota empanizados y fritos al punto.'),
  ('Chicharrones y Jaleas', 15, 'Chicharrón de Langostinos', 28.00, 'Colas de langostinos crocantes con crema tártara.'),
  ('Chicharrones y Jaleas', 16, 'Jalea Real Filete', 32.00, 'Generosa fuente marina crocante con filete de pescado.'),
  ('Chicharrones y Jaleas', 17, 'Jalea Real Pescado Entero', 40.00, 'Pescado entero frito cubierto de mariscos crujientes.'),

  -- ARROCES
  ('Arroces', 18, 'Arroz con Mariscos', 18.00, 'Arroz criollo con mixtura de mariscos, ají amarillo y vino blanco.'),
  ('Arroces', 19, 'Chaufa de Mariscos', 18.00, 'Arroz chaufa al wok con mixtura de mariscos y cebollita china.'),
  ('Arroces', 20, 'Chaufa de Pescado', 15.00, 'Chaufa tradicional salteado con dados de pescado dorados.'),

  -- FILETES Y PESCADOS
  ('Filetes y Pescados', 21, 'Filete a la Plancha', 15.00, 'Filete de pescado fresco a la plancha con papas y arroz.'),
  ('Filetes y Pescados', 22, 'Filete Apanado', 17.00, 'Filete de pescado empanizado con guarnición.'),
  ('Filetes y Pescados', 23, 'Filete a lo Macho', 22.00, 'Filete de pescado bañado en cremosa salsa picante de mariscos.'),
  ('Filetes y Pescados', 24, 'Pescado Entero Frito', 30.00, 'Pescado entero de temporada dorado con patacones o papas.'),

  -- SOPAS
  ('Sopas', 25, 'Parihuela Especial', 20.00, 'Sustanciosa sopa marina con pescado y frutos del mar.'),
  ('Sopas', 26, 'Sudado de Pescado', 18.00, 'Guiso norteño de pescado con chicha de jora, tomate y cebolla.'),
  ('Sopas', 27, 'Chupe de Pescado', 22.00, 'Chupe tradicional con queso, leche, choclo y huevo escalfado.'),
  ('Sopas', 28, 'Chilcano Especial', 12.00, 'Caldo concentrado de pescado con limón, cebolla y canchita.'),

  -- PLATOS CRIOLLOS Y FONDOS
  ('Platos Criollos y Fondos', 29, 'Lomo Saltado Clásico', 18.00, 'Carne jugosa al wok con cebolla, tomate, papas fritas y arroz.'),
  ('Platos Criollos y Fondos', 30, 'Lomo Saltado con Chaufa', 20.00, 'Lomo saltado tradicional servido sobre una base de arroz chaufa.'),
  ('Platos Criollos y Fondos', 31, 'Fetuccini a la Huancaína con Lomo', 18.00, 'Pasta al dente en salsa huancaína artesanal con lomo al jugo.'),
  ('Platos Criollos y Fondos', 32, 'Churrasco a lo Pobre', 20.00, 'Corte de churrasco con plátano frito, huevo montado y papas.'),
  ('Platos Criollos y Fondos', 33, 'Pechuga a la Plancha', 17.00, 'Filete de pechuga jugosa con papas fritas y ensalada fresca.'),
  ('Platos Criollos y Fondos', 34, 'Chaufa de Carne', 15.00, 'Arroz salteado al wok con trozos de carne y aceite de ajonjolí.'),
  ('Platos Criollos y Fondos', 35, 'Chaufa de Pollo', 12.00, 'Clásico arroz chaufa de pollo con tortilla de huevo.'),

  -- HAMBURGUESAS
  ('Hamburguesas', 36, 'Hamburguesa Clásica de Carne', 10.00, 'Carne artesanal de res, lechuga, tomate y cremas.'),
  ('Hamburguesas', 37, 'Hamburguesa Royal Clásica', 13.00, 'Carne artesanal, queso cheddar, huevo frito y jamón.'),
  ('Hamburguesas', 38, 'Hamburguesa Royal Hawaiana', 14.00, 'Carne artesanal, piña a la parrilla, queso y jamón.'),
  ('Hamburguesas', 39, 'Hamburguesa a lo Pobre', 14.00, 'Carne artesanal con plátano frito y huevo montado.'),
  ('Hamburguesas', 40, 'Hamburguesa Filete de Pollo', 10.00, 'Pechuga de pollo a la plancha con lechuga y tomate.'),

  -- PIQUEOS Y ALITAS
  ('Piqueos y Alitas', 41, 'Ronda de Alitas (12 pzas)', 28.00, 'Alitas crocantes bañadas en salsa BBQ, Acevichada o Búfalo.'),
  ('Piqueos y Alitas', 42, 'Porción de Alitas (6 pzas)', 14.00, '6 alitas bañadas en la salsa de tu preferencia.'),
  ('Piqueos y Alitas', 43, 'Alitas Crispy (6 pzas)', 15.00, 'Alitas estilo crispy super crujientes.'),
  ('Piqueos y Alitas', 44, 'Chicharrón de Pollo', 15.00, 'Trozos de pechuga frita dorada con papas fritas.'),
  ('Piqueos y Alitas', 45, 'Salchipapa Clásica', 9.00, 'Papas fritas con salchicha en rodajas y cremas.'),
  ('Piqueos y Alitas', 46, 'Salchipapa a lo Pobre', 12.00, 'Salchipapa clásica con huevo frito y plátano frito.'),

  -- TEQUEÑOS
  ('Tequeños', 47, 'Tequeños de Lomo (12 uni)', 18.00, '12 tequeños rellenos de lomo saltado con crema huancaína.'),
  ('Tequeños', 48, 'Tequeños de Queso (12 uni)', 13.00, '12 tequeños crocantes rellenos de queso con guacamole.'),
  ('Tequeños', 49, 'Tequeños Mixtos (12 uni)', 15.00, '6 tequeños de lomo y 6 de queso.'),

  -- GUARNICIONES
  ('Guarniciones', 50, 'Porción de Papas Fritas', 7.00, 'Papas fritas crocantes.'),
  ('Guarniciones', 51, 'Porción de Yucas con Huancaína', 10.00, 'Yucas doradas crocantes con crema de ají huancaína.'),

  -- CARA 2: COCTELERÍA Y BEBIDAS
  ('Cócteles', 52, 'Pisco Sour Clásico', 15.00, 'Pisco quebranta, limón fresco, jarabe de goma y amargo.'),
  ('Cócteles', 53, 'Chilcano de Maracuyá', 15.00, 'Pisco, pulpa de maracuyá y ginger ale bien fría.'),
  ('Cócteles', 54, 'Machupicchu', 15.00, 'Coctel multicolor con pisco, licor de menta, naranja y granadina.'),
  ('Cócteles', 55, 'Mojito Clásico', 15.00, 'Ron blanco, hierbabuena fresca, azúcar, limón y soda.'),
  ('Cócteles', 56, 'Daiquiri de Fresa', 15.00, 'Ron blanco con fresas frescas frappé.'),
  ('Cócteles', 57, 'Sangría Especial (Jarra 1L)', 28.00, 'Jarra de vino tinto con frutas de temporada maceradas.'),
  ('Cócteles', 58, 'Copa de Sangría', 10.00, 'Copa individual de sangría de la casa.'),
  ('Cócteles', 59, 'Margarita', 15.00, 'Tequila, triple sec y zumo de limón escarchado con sal.'),

  -- CERVEZAS
  ('Cervezas', 60, 'Pilsen Callao 630ml', 9.00, 'Botella grande helada.'),
  ('Cervezas', 61, 'Cusqueña Trigo 620ml', 10.00, 'Cerveza de trigo artesanal.'),
  ('Cervezas', 62, 'Cusqueña Negra 620ml', 10.00, 'Cerveza negra malteada.'),

  -- BEBIDAS Y JUGOS
  ('Bebidas y Jugos', 63, 'Limonada Frozen (1 Litro)', 12.00, 'Jarra helada frappé de limón fresco.'),
  ('Bebidas y Jugos', 64, 'Maracuyá Frozen (1 Litro)', 14.00, 'Jarra frozen de pulpa de maracuyá natural.'),
  ('Bebidas y Jugos', 65, 'Chicha Morada (1 Litro)', 10.00, 'Chicha morada casera de maíz morado, piña y canela.'),
  ('Bebidas y Jugos', 66, 'Jugo de Papaya', 9.00, 'Jugo natural de papaya fresca.'),
  ('Bebidas y Jugos', 67, 'Inca Kola Gordita', 5.00, 'Gaseosa Inca Kola vidrio personal.'),
  ('Bebidas y Jugos', 68, 'Inca Kola 1 Litro', 7.00, 'Botella de 1 litro retornable o descartable.'),
  ('Bebidas y Jugos', 69, 'Coca Cola 1 Litro', 7.00, 'Botella de 1 litro.'),

  -- BEBIDAS CALIENTES
  ('Bebidas Calientes', 70, 'Café Pasado', 3.00, 'Café pasado tradicional caliente.'),
  ('Bebidas Calientes', 71, 'Café con Leche', 5.00, 'Taza caliente de café con leche entera.'),
  ('Bebidas Calientes', 72, 'Infusión (Té / Manzanilla / Anís)', 2.00, 'Infusión caliente en taza.')
) AS p(cat_nombre, codigo, nombre, precio, descripcion)
JOIN categoria c ON c.nombre = p.cat_nombre;
