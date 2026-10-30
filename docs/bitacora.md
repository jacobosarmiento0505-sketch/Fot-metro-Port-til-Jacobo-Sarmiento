# Bitácora del proyecto — Fotómetro portátil para análisis de muestras

## Parte I

- Definición del problema: fotómetro portátil de bajo costo para análisis de
  muestras líquidas (tipo de muestra abierto, a definir con mayor detalle
  junto a los profesores del curso).
- Objetivos, requerimientos, diagrama de bloques y plan de pruebas
  entregados (ver `docs/informes/`).
- Lista de materiales inicial propuesta: fotodiodo BPW34 + amplificador
  operacional (LM324) como front-end analógico, LED de excitación, ESP32
  como controlador, pantalla para lectura de resultados.
- Reunión con los profesores para validar la propuesta de materiales y el
  concepto del prototipo (boceto en pizarra con la disposición física del
  equipo).

## Parte II

- Se retomó el diseño para pasar a esquemático y PCB en KiCad, según el
  Anexo 2 del enunciado (pistas/espaciados mínimos 0.8 mm, 4 orificios de
  montaje M3, PCB de una sola cara B.Cu, repositorio público en GitHub).
- **Cambio de diseño:** los profesores sugirieron reemplazar el front-end
  analógico (fotodiodo + amplificador operacional) por un sensor de color
  digital I2C **TCS34725** (módulo breakout HW-393), para simplificar el
  diseño electrónico y el firmware del equipo. Se adoptó esta sugerencia;
  el detalle de la decisión está en `docs/informes/`.
- Se definió la arquitectura final:
  - Alimentación: batería Li-Po → interruptor SPDT → módulo cargador/boost
    TP4056 (salida 5V) → placa ESP32 (regulador interno a 3.3V).
  - Bus I2C compartido (SDA/SCL, pull-ups 4.7kΩ) entre ESP32, OLED SSD1306
    y el sensor TCS34725.
  - Dos pulsadores con pull-up 10kΩ y capacitor de 100nF para antirrebote:
    CALIBRAR y MEDIR.
  - Capacitores de desacople: 100µF de bulto en cada riel (3.3V y 5V) y
    100nF locales junto a cada módulo.
- Se construyó el esquemático completo en KiCad (19 componentes, 9 redes)
  usando conectores genéricos tipo header para cada módulo comercial
  (ESP32, OLED, TCS34725, cargador), siguiendo el criterio de "PCB de
  integración" explícitamente permitido por el enunciado.
- Se diseñó el layout de PCB de una sola cara (B.Cu), con separación
  generosa entre footprints para cumplir el espaciado mínimo de 0.8mm, 4
  orificios de montaje M3 cerca de las esquinas, y enrutado automático de
  las pistas principales (alimentación, I2C, botones).
- Se generaron los archivos de fabricación: Gerbers, taladro, STEP, BOM y
  vistas en PDF/PNG del esquemático y la placa.

## Retroalimentación del profesor y versión 2 (30 de octubre de 2026)

- El profesor pidió cuatro cambios: textos en el esquemático, botones
  cableados como en su ejemplo, ESP32 (J3) con todos sus pines conectados y una
  placa mucho más compacta. Se rehízo el esquemático (hoja A3, con cables,
  textos y cuadro de título) y la PCB (de ~175 x 220 mm a ~117 x 77 mm, todas las
  conexiones ruteadas en B.Cu). Revisada en KiCad, el profesor la aprobó.
- Cambio de footprint: el interruptor SW1 pasó a la huella Würth WS-SLTV con pitch
  de 2,54 mm (la anterior tenía pads a 2 mm y no permitía los 0,8 mm de separación).
- El profesor pidió subir el proyecto a GitHub para revisarlo; se creó el
  repositorio público y se subieron los archivos.
- Revisión contra el enunciado de la Parte II: el DRC marcaba 42 avisos de
  separación (0,4–0,8 mm). Se volvió a rutear con margen estricto de 0,8 mm
  (placa de ~121 x 80 mm): **0 violaciones**, 40/40 conexiones, 0 cortos.
- Se agregaron: serigrafía (nombre, versión, equipo, leyenda de pines),
  bibliotecas propias en `electronica/libraries/` (símbolos y footprints),
  hojas de datos, imágenes de cara superior, cara inferior, vista 3D y DRC,
  zip de Gerbers y taladro, e informe en PDF.
- Equipo 2, sección 1: Jacobo Sarmiento, Sofía Kotoras y Jimena Otero.
- Pendiente para la siguiente etapa: fabricación en la CNC, montaje, pruebas de
  alimentación e I2C y firmware.
