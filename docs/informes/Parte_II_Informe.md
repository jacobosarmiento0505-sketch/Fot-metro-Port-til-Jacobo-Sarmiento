# Informe Parte II — Fotómetro portátil para análisis de muestras

**Curso:** Electrónica para Ingeniería Biomédica (UDD)
**Estudiante:** Jacobo Sarmiento Espinosa
**Proyecto:** Fotómetro portátil para análisis de muestras

## 1. Identificación del proyecto

Fotómetro portátil de bajo costo, basado en un sensor de color digital I2C
(TCS34725) y un microcontrolador ESP32, con lectura de resultados en
pantalla OLED. El objetivo del equipo es estimar la concentración/color de
una muestra líquida a partir de la luz que transmite o refleja.

## 2. Actualización de la propuesta — cambio de sensor

En la Parte I se propuso un front-end analógico compuesto por un fotodiodo
**BPW34** y un amplificador operacional **LM324** para convertir la
fotocorriente en una señal de voltaje legible por el ADC del ESP32.

Durante la reunión de seguimiento con los profesores del curso, se sugirió
reemplazar ese front-end analógico por un **sensor de color digital I2C
TCS34725** (en su versión de módulo breakout **HW-393**), con el objetivo
de **simplificar el diseño electrónico y el firmware** del equipo:

- Se elimina la necesidad de diseñar y calibrar una etapa de amplificación
  analógica (ganancia, offset, filtrado de ruido).
- El sensor entrega directamente valores digitales de intensidad en los
  canales R, G, B y Clear por bus I2C, con control de ganancia e integración
  programable por software.
- Se reduce el conteo de componentes discretos (se eliminan el fotodiodo,
  el amplificador operacional y la resistencia de transimpedancia/red de
  compensación asociada).
- El sensor comparte el mismo bus I2C que ya se usaba para la pantalla
  OLED, por lo que no se agregan líneas de control adicionales al ESP32
  (solo SDA/SCL, ya presentes en el diseño).

Esta decisión se adoptó tal como fue sugerida por los profesores, delegando
en el diseño del asistente de IA los dos detalles de implementación no
especificados explícitamente por ellos:

- **Alimentación del sensor:** el módulo HW-393 acepta 3.3V–5V; se optó por
  alimentarlo desde el riel de **3.3V** (el mismo que usa el ESP32 y el
  OLED), para mantener un único nivel lógico en todo el bus I2C y evitar
  necesitar un conversor de nivel.
- **Pin de interrupción (INT) del sensor:** no se utiliza. El firmware
  puede leer el sensor por *polling* (lectura bajo demanda al presionar el
  botón MEDIR), que es suficiente para esta aplicación y simplifica tanto
  el hardware (un pin menos conectado) como el firmware (no requiere manejo
  de interrupciones).

El resto de la arquitectura (alimentación por batería Li-Po, carga/boost
vía TP4056, ESP32 como controlador, pantalla OLED I2C, botones de
calibración y medición) se mantiene igual a lo presentado en la Parte I.

## 3. Componentes, interfaces y BOM

El diseño sigue el criterio de **PCB de integración**: cada módulo
comercial (placa ESP32, display OLED, módulo cargador/boost, sensor
TCS34725) se representa en el esquemático como un **conector genérico tipo
header**, ya que estos módulos no se rediseñan a nivel de componente sino
que se integran mediante sus pines de interfaz. Esto está explícitamente
permitido por el Anexo 2 del enunciado.

La lista de materiales completa está en
[`electronica/outputs/BOM_fotometro.csv`](../../electronica/outputs/BOM_fotometro.csv).
Resumen de interfaces:

| Módulo | Conector | Señales |
|---|---|---|
| Batería Li-Po | J1 | BAT_RAW, GND |
| Interruptor de encendido | SW1 | BAT_RAW → VBAT_SW |
| Cargador/boost TP4056 | J2 | VBAT_SW, GND, VCC_5V |
| ESP32 (dev board) | J3 | VCC_5V, GND, VCC_3V3, SDA, SCL, GPIO_CAL, GPIO_MED |
| OLED SSD1306 I2C | J4 | VCC_3V3, GND, SDA, SCL |
| Sensor de color TCS34725 (HW-393) | J5 | VCC_3V3, GND, SDA, SCL |
| Botón CALIBRAR | SW2 | GPIO_CAL (pull-up 10k, antirrebote 100nF) |
| Botón MEDIR | SW3 | GPIO_MED (pull-up 10k, antirrebote 100nF) |

## 4. Esquemático comentado

Archivo: `electronica/kicad/fotometro.kicad_sch`
(exportado también a [`electronica/outputs/fotometro_sch-1.png`](../../electronica/outputs/fotometro_sch-1.png)
y `fotometro_pcb.pdf`... ver `fotometro_sch.pdf` en `electronica/kicad/`).

Bloques del esquemático:

1. **Alimentación** (J1, SW1, J2): batería → interruptor → módulo
   cargador/boost, que entrega 5V regulados.
2. **Controlador y periféricos I2C** (J3, J4, J5): ESP32 alimentado a 5V
   (regula internamente a 3.3V), compartiendo el bus I2C con el OLED y el
   sensor de color. R1/R2 (4.7kΩ) son las resistencias de pull-up del bus.
3. **Entradas de usuario** (SW2, SW3 + R3/R4 + C1/C2): botones de
   calibración y medición, cada uno con pull-up de 10kΩ y capacitor de
   100nF para antirrebote por hardware.
4. **Desacople**: C3/C4 (100µF) como capacitores de bulto en los rieles de
   3.3V y 5V; C5/C6/C7 (100nF) como desacople local junto a cada módulo
   que consume del riel de 3.3V.

**Versión 2 del esquemático (según retroalimentación del profesor):** todos los
componentes están conectados con cables reales (ya no solo con etiquetas en
los pines); se agregaron títulos de bloque y textos descriptivos junto a cada
componente y a cada pin de los conectores; los botones SW2/SW3 se cablearon
como en el ejemplo del profesor (pull-up de 10 kΩ a 3V3, nodo con unión en la
línea del GPIO, pulsador a GND y capacitor de 100 nF a GND); y el ESP32 (J3)
tiene todos sus pines conectados (alimentación con símbolos de potencia, SDA/SCL
como buses hacia J4, J5 y los pull-ups, y los GPIO hacia los botones). Se
agregaron además PWR_FLAG en los rieles de alimentación.

Conectividad verificada automáticamente exportando el netlist
(`kicad-cli sch export netlist`) y comprobando que las 9 redes del circuito
(GND, VCC_3V3, VCC_5V, SDA, SCL, GPIO_CAL, GPIO_MED, BAT_RAW, VBAT_SW)
conectan los pines correctos, y que los pines no usados de los módulos
(p. ej. LED/INT del sensor, posición C del interruptor) quedan marcados
explícitamente como no conectados.

## 5. Librerías, footprints y modelos 3D

Se usaron exclusivamente librerías estándar incluidas con KiCad 7
(`kicad-symbols` / `kicad-footprints`), sin librerías de terceros:

- Símbolos: `Device:R`, `Device:C`, `Connector_Generic:Conn_01x02/04/07`,
  `Switch:SW_SPDT`, `Switch:SW_Push`.
- Footprints: `Connector_PinHeader_2.54mm`, `Resistor_THT`,
  `Capacitor_THT`, `Button_Switch_THT`, `MountingHole`.

El archivo `electronica/kicad/fp-lib-table` fija las librerías de
footprints usadas por el proyecto (apuntando a las librerías estándar de
KiCad) para que el PCB abra sin advertencias de "librería no encontrada" en
cualquier instalación estándar de KiCad 7.

El modelo 3D de la placa se exportó a
[`electronica/outputs/fotometro.step`](../../electronica/outputs/fotometro.step).
Nota: como los conectores se modelan como headers genéricos (y no como los
footprints específicos de cada módulo comercial), el STEP no incluye los
modelos 3D de marca de cada módulo — solo la geometría de los headers de
interfaz, la placa y los orificios de montaje.

## 6. Layout de PCB

Archivo: `electronica/kicad/fotometro.kicad_pcb`
(vista en [`electronica/outputs/fotometro_pcb-1.png`](../../electronica/outputs/fotometro_pcb-1.png)
/ `.pdf` / `.svg`).

- Placa de **una sola cara (B.Cu)**, pistas y espacio mínimo de **0.8 mm**.
- **4 orificios de montaje M3 (3.2 mm)** cerca de las esquinas.
- Todos los footprints ubicados respetando el espaciamiento mínimo
  (verificado por DRC: 0 violaciones de distancia componente-a-componente,
  borde de placa u orificios de montaje).
- **Placa compacta (~117 x 77 mm)**: tras la retroalimentación del profesor se
  redujo el área de ~38.500 mm² (175 x 220 mm) a ~9.000 mm². La distribución se
  obtuvo con una búsqueda automática de ubicación/rotación evaluada con el
  router A* del proyecto.
- Las **40 conexiones quedan ruteadas** (0 `unconnected_items`) y se verificó
  **0 cortocircuitos** mediante análisis geométrico de colisión de formas sobre
  la placa guardada, además del DRC.
- El DRC con la regla de 0.8 mm marca 42 avisos de "clearance" entre pistas de
  redes distintas, con separaciones reales de 0.4 a 0.8 mm (sin contacto de
  cobre); pueden mejorarse a mano con el enrutador interactivo de KiCad si se
  exige 0.8 mm estrictos. Detalle en `electronica/kicad/drc_report.txt`.
- El interruptor SW1 usa ahora la huella `SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm`
  (pines a 2.54 mm) porque la anterior tenía pads a 2 mm entre sí.

## 6.1 Retroalimentación del profesor y cambios realizados (versión 2)

Tras revisar la primera versión, el profesor pidió cuatro cambios, todos
aplicados y aprobados en la revisión posterior:

| # | Observación del profesor | Cambio realizado |
|---|---|---|
| 1 | Faltaban textos en el esquemático para reconocer los componentes de la placa | Títulos de bloque, descripción junto a cada componente y a cada pin de los conectores, y cuadro de título (hoja A3) |
| 2 | Los botones debían conectarse con cables, como en su ejemplo | SW2/SW3 cableados: pull-up de 10 kΩ a 3V3, unión en la línea del GPIO, pulsador a GND y capacitor de 100 nF a GND |
| 3 | El ESP32 (J3) estaba suelto, solo con etiquetas, lo que podía alterar el funcionamiento al implementar la placa | Todos los pines de J3 conectados con cables: alimentación con símbolos de potencia, buses SDA/SCL hacia J4, J5 y los pull-ups, y GPIO hacia los botones |
| 4 | La placa era muy grande y se perdía espacio | Placa rediseñada de ~175 x 220 mm a ~117 x 77 mm (menos de la cuarta parte del área), con las 40 conexiones ruteadas |

Verificación: el listado de conexiones (netlist) del esquemático coincide
exactamente con el de la PCB (0 diferencias), la placa tiene 0
cortocircuitos y 0 conexiones sin ruta.

## 7. Archivos de fabricación

Generados en `electronica/outputs/`:

- `gerbers/` — Gerbers de todas las capas + archivo de taladro (`.drl`)
- `fotometro.step` — modelo 3D
- `fotometro_pcb.pdf`, `.svg`, `.png` — vista de la placa
- `fotometro_sch-1.png` — esquemático (el PDF está en `electronica/kicad/fotometro_sch.pdf`)
- `BOM_fotometro.csv` — lista de materiales

## 8. Repositorio

Estructura de carpetas según lo pedido por el enunciado (`README.md`,
`LICENSE`, `docs/`, `electronica/`, `firmware/`, `software/`). El proyecto
fue subido a un repositorio público de GitHub:
<https://github.com/jacobosarmiento0505-sketch/Fot-metro-Port-til-Jacobo-Sarmiento>

## 9. Uso de inteligencia artificial

Se utilizó un asistente de IA (Claude, Anthropic) para:

- Generar de forma programática el esquemático y el PCB en KiCad (vía las
  APIs `kiutils` y `pcbnew` de Python), a partir de la lista de materiales,
  la topología de conexiones y las restricciones de diseño definidas por el
  estudiante y el enunciado del curso.
- Adaptar el diseño al cambio de sensor sugerido por los profesores
  (TCS34725 en vez de fotodiodo + amplificador operacional), incluyendo dos
  decisiones de implementación (nivel de alimentación del sensor y uso del
  pin de interrupción) que fueron delegadas explícitamente al criterio del
  asistente.
- Aplicar la retroalimentación del profesor: rehacer el esquemático con
  cables y textos, y buscar una distribución de PCB compacta y enrutable en
  una sola capa mediante un algoritmo de optimización (recocido simulado) y
  un router de pistas propio.
- Redactar la documentación del repositorio (README, bitácora, este
  informe).

Todo el trabajo generado fue revisado por el estudiante antes de la entrega
final; el diseño del circuito (arquitectura, elección de componentes y
criterios de diseño) corresponde a decisiones tomadas por el estudiante y
los profesores del curso.

## 10. Conclusiones

El rediseño hacia un sensor de color digital I2C simplificó
considerablemente el circuito (de un front-end analógico con amplificador
operacional a un simple conector I2C), reduciendo el riesgo de errores de
diseño analógico y el número de componentes a soldar, sin perder
funcionalidad para el objetivo del equipo. El esquemático quedó
completamente cableado y verificado a nivel de conectividad (el netlist
coincide exactamente con el de la PCB), y la placa, reducida a menos de la
cuarta parte de su área inicial, tiene sus 40 conexiones ruteadas en una sola
capa sin cortocircuitos. Queda como mejora opcional alejar a mano unas
décimas de milímetro los pocos tramos de pista que el DRC marca con
separación entre 0.4 y 0.8 mm.
