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
- Pendiente para el estudiante: revisar el PCB en KiCad y terminar de
  resolver manualmente, con el enrutador interactivo, los pocos cruces de
  pistas que el DRC automático marca (ver nota en el README y en
  `electronica/kicad/drc_report.txt`).
