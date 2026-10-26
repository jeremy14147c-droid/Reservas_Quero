-- =====================================================================
-- DATOS INICIALES REALES: Quero Gastrobar (Lima, Perú)
-- Obtenidos de la carta oficial del restaurante.
-- =====================================================================
INSERT INTO config_local
  (config_id, nombre_local, aforo_personas, total_mesas, personas_por_mesa, duracion_estadia_min,
   franja_min, tolerancia_min, umbral_preparacion_min, max_reservas_web_por_telefono, umbral_alerta_pct,
   hora_apertura, hora_cierre, dias_max_anticipacion, porcentaje_reservable, abierto,
   yape_numero, yape_titular, mensaje_pago)
VALUES
  (1, 'Quero Gastrobar', 48, 12, 4, 90, 30, 15, 20, 2, 80,
   '12:00', '23:00', 3, NULL, TRUE,
   '996908138', 'Quero Gastrobar', 'Envía tu comprobante de pago al WhatsApp 996908138 indicando tu código de pedido.')
ON CONFLICT (config_id) DO UPDATE SET
  nombre_local = EXCLUDED.nombre_local,
  yape_numero = EXCLUDED.yape_numero,
  yape_titular = EXCLUDED.yape_titular,
  mensaje_pago = EXCLUDED.mensaje_pago,
  hora_cierre = EXCLUDED.hora_cierre;

-- Categorías oficiales
INSERT INTO categoria (nombre, orden, activa) VALUES
  ('Ceviches', 1, TRUE),
  ('Chicharrones y Jaleas', 2, TRUE),
  ('Arroces', 3, TRUE),
  ('Platos Criollos y Fondos', 4, TRUE),
  ('Hamburguesas', 5, TRUE),
  ('Piqueos y Alitas', 6, TRUE),
  ('Tequeños', 7, TRUE),
  ('Cócteles', 8, TRUE),
  ('Bebidas y Jugos', 9, TRUE)
ON CONFLICT (nombre) DO NOTHING;

-- Platos oficiales de Quero Gastrobar
INSERT INTO plato (categoria_id, nombre, precio, descripcion, disponible, activo)
SELECT c.categoria_id, p.nombre, p.precio, p.descripcion, TRUE, TRUE
FROM (VALUES
  ('Ceviches', 'Ceviche de Pescado', 25.00, 'Pescado fresco del día con cebolla, camote y choclo desgranado.'),
  ('Ceviches', 'Ceviche Mixto', 28.00, 'Pescado y mixtura de mariscos marinados en zumo de limón fresco.'),
  ('Ceviches', 'Ceviche de Pota', 15.00, 'Tiras de pota fresca con toque picante y crocante.'),
  ('Ceviches', 'Leche de Tigre', 15.00, 'Concentrado de ceviche con trozos de pescado y canchita.'),
  ('Chicharrones y Jaleas', 'Chicharrón de Pescado', 22.00, 'Trozos de pescado frito crocante acompañados de yuca y sarza criolla.'),
  ('Chicharrones y Jaleas', 'Chicharrón Mixto', 25.00, 'Mariscos y pescado crujiente con tártara casera.'),
  ('Chicharrones y Jaleas', 'Jalea Real Filete', 32.00, 'Generosa fuente marina crocante con filete de pescado.'),
  ('Arroces', 'Arroz con Mariscos', 18.00, 'Arroz criollo con mariscos, ají amarillo y vino blanco.'),
  ('Arroces', 'Chaufa de Mariscos', 18.00, 'Arroz chaufa al wok con mixtura de mariscos y cebolla china.'),
  ('Arroces', 'Chaufa de Pescado', 15.00, 'Chaufa clásico con dados de pescado dorados.'),
  ('Platos Criollos y Fondos', 'Lomo Saltado', 18.00, 'Tiras de carne flambeada al wok con cebolla, tomate, papas fritas y arroz.'),
  ('Platos Criollos y Fondos', 'Lomo Saltado con Chaufa', 20.00, 'Fusión de lomo saltado tradicional servido con arroz chaufa.'),
  ('Platos Criollos y Fondos', 'Fetuccini a la Huancaína con Lomo', 18.00, 'Pasta en cremosa salsa huancaína con trozos de lomo al jugo.'),
  ('Platos Criollos y Fondos', 'Churrasco a lo Pobre', 20.00, 'Churrasco a la plancha con plátano frito, huevo montado, papas y arroz.'),
  ('Platos Criollos y Fondos', 'Pechuga a la Plancha', 17.00, 'Filete de pechuga jugosa con papas fritas y ensalada fresca.'),
  ('Hamburguesas', 'Hamburguesa Clásica de Carne', 10.00, 'Carne artesanal, tomate, lechuga y salsas de la casa.'),
  ('Hamburguesas', 'Hamburguesa Royal Clásica', 13.00, 'Carne artesanal, queso, huevo frito y jamón.'),
  ('Hamburguesas', 'Hamburguesa Royal Hawaiana', 14.00, 'Carne artesanal, piña a la plancha, queso y jamón.'),
  ('Hamburguesas', 'Hamburguesa a lo Pobre', 14.00, 'Carne artesanal con plátano frito y huevo montado.'),
  ('Piqueos y Alitas', 'Ronda de Alitas (12 pzas)', 28.00, 'Alitas bañadas en salsas BBQ, Acevichada, Maracuyá o Búfalo.'),
  ('Piqueos y Alitas', 'Porción de Alitas (6 pzas)', 14.00, '6 unidades de alitas en salsa a elección.'),
  ('Piqueos y Alitas', 'Chicharrón de Pollo', 15.00, 'Trozos crocantes de pollo acompañados de papas fritas.'),
  ('Piqueos y Alitas', 'Salchipapa Clásica', 9.00, 'Papas fritas crocantes con hot dog en rodajas.'),
  ('Piqueos y Alitas', 'Salchipapa a lo Pobre', 12.00, 'Salchipapa con huevo frito y plátano frito.'),
  ('Tequeños', 'Tequeños de Lomo (12 uni)', 18.00, '12 tequeños rellenos de lomo saltado con crema de palta o huancaína.'),
  ('Tequeños', 'Tequeños de Queso (12 uni)', 13.00, '12 tequeños crocantes rellenos de queso.'),
  ('Tequeños', 'Tequeños Mixtos (12 uni)', 15.00, '6 de lomo y 6 de queso.'),
  ('Cócteles', 'Pisco Sour Clásico', 15.00, 'Pisco quebranta, limón, jarabe de goma y amargo de angostura.'),
  ('Cócteles', 'Chilcano de Maracuyá', 15.00, 'Pisco, zumo de maracuyá y ginger ale bien helado.'),
  ('Cócteles', 'Machupicchu', 15.00, 'Trago multicolor con pisco, menta, naranja y granadina.'),
  ('Cócteles', 'Mojito Clásico', 15.00, 'Ron blanco, hierbabuena fresca, limón y soda.'),
  ('Cócteles', 'Daiquiri de Fresa', 15.00, 'Ron blanco, fresas frescas y hielo frappé.'),
  ('Cócteles', 'Sangría Especial (Jarra 1L)', 28.00, 'Vino tinto, frutas maceradas y toques cítricos.'),
  ('Bebidas y Jugos', 'Limonada Frozen (1 Litro)', 12.00, 'Refrescante jarra frozen de limón.'),
  ('Bebidas y Jugos', 'Maracuyá Frozen (1 Litro)', 14.00, 'Jarra frozen de maracuyá natural.'),
  ('Bebidas y Jugos', 'Chicha Morada (1 Litro)', 10.00, 'Chicha natural de maíz morado con frutas.'),
  ('Bebidas y Jugos', 'Inca Kola Gordita', 5.00, 'Gaseosa Inca Kola personal.')
) AS p(cat_nombre, nombre, precio, descripcion)
JOIN categoria c ON c.nombre = p.cat_nombre
WHERE NOT EXISTS (SELECT 1 FROM plato WHERE lower(plato.nombre) = lower(p.nombre));
