# Fotómetro portátil para análisis de muestras

Proyecto del curso **Electrónica para Ingeniería Biomédica** (UDD) — diseño y
construcción de un fotómetro portátil de bajo costo, basado en un sensor de
color digital I2C y un microcontrolador ESP32, con pantalla OLED para
lectura directa de resultados.

## Estado del proyecto

- **Parte I** — propuesta, objetivos, requerimientos, diagrama de bloques y
  plan de pruebas: entregada (ver `docs/informes/`).
- **Parte II** — esquemático y layout de PCB en KiCad, lista de materiales
  (BOM) y archivos de fabricación: contenido de este repositorio.

## Resumen del hardware

El equipo mide la absorbancia/color de una muestra usando un sensor de
color RGB+Clear por I2C (**TCS34725**, módulo breakout HW-393), controlado
por una placa de desarrollo **ESP32**. Los resultados se muestran en una
pantalla **OLED SSD1306 (I2C, 128x64)**. Dos pulsadores permiten calibrar
con un blanco de referencia y disparar una medición. La alimentación es por
batería Li-Po, con carga/boost mediante un módulo TP4056 + convertidor
5V, regulado a 3.3V por el propio módulo ESP32.

> **Cambio de diseño respecto a la Parte I:** el front-end analógico
> original (fotodiodo BPW34 + amplificador operacional LM324) fue
> reemplazado por el sensor digital TCS34725, por sugerencia de los
> profesores del curso, para simplificar el diseño electrónico y de
> firmware. El detalle de este cambio está documentado en
> `docs/informes/`.

## Estructura del repositorio

```
.
├── README.md
├── LICENSE
├── docs/
│   ├── datasheets/      # hojas de datos de los componentes usados
│   ├── bitacora.md      # bitácora de avance del proyecto
│   └── informes/        # informes entregables (Parte I, Parte II)
├── electronica/
│   ├── kicad/           # proyecto KiCad: esquemático (.kicad_sch) y PCB (.kicad_pcb)
│   ├── libraries/       # librerías/símbolos o footprints propios (si los hay)
│   └── outputs/         # archivos de fabricación exportados (gerbers, STEP, BOM, PDFs)
├── firmware/            # firmware del ESP32 (Arduino/ESP-IDF)
└── software/            # software de apoyo (análisis de datos, scripts, etc.)
```

## Abrir el proyecto en KiCad

1. Instalar [KiCad 7](https://www.kicad.org/download/) (o superior).
2. Abrir `electronica/kicad/fotometro.kicad_pro`.
3. El esquemático (`fotometro.kicad_sch`) y el layout de PCB
   (`fotometro.kicad_pcb`) se abren desde ahí.

### Estado del enrutado de la PCB

La placa es de **una sola cara (B.Cu)**, pistas y espacios mínimos de
**0.8 mm**, con 4 orificios de montaje M3 (3.2 mm) — según lo pedido por el
Anexo 2 del enunciado. El esquemático está limpio (conectividad verificada
con `kicad-cli sch export netlist`) y la ubicación de todos los
footprints respeta los espaciamientos mínimos.

La placa se **rediseñó más compacta** a partir de la retroalimentación del
profesor: pasó de ~175 x 220 mm (38.500 mm²) a **~121 x 80 mm
(~9.700 mm²)**, cerca de la cuarta parte del área anterior. La distribución
se obtuvo con una búsqueda automática (recocido simulado sobre la ubicación y
rotación de cada componente, evaluando el ruteo real con el router A* del
proyecto) y el ruteo final se repitió con margen estricto de 0,8 mm.

Resultado del enrutado (verificado sobre el archivo guardado):

- **Las 40 conexiones están ruteadas** — 0 pines sin conectar.
- **0 cortocircuitos** y **0 violaciones de separación**: el DRC con las reglas de
  0,8 mm de ancho y 0,8 mm de separación no marca errores.
- Todas las pistas están en **B.Cu** (0 en F.Cu), de 0,8 mm de ancho.
- Queda **1 advertencia** `copper_sliver` (B.Cu), documentada en el informe.
- Serigrafía con nombre del proyecto, versión (v2.0), equipo, integrantes,
  leyenda de pines de J1–J5 y pin 1 como pad cuadrado.

Cambio de huella: el interruptor SW1 pasó a `SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm`
(pines a 2.54 mm; el CK OS102011MS2Q anterior tenía pads a solo 2 mm entre sí, lo
que incumple por sí solo los 0.8 mm de separación). En el esquemático el pin 1 de SW1
es el contacto común (centro de la huella) y el pin 2 la salida.

## Archivos de fabricación

En `electronica/outputs/` se incluyen:

- `gerbers/` — Gerbers de las capas usadas + archivo de taladro (`.drl`)
- `fotometro_gerbers_y_taladro.zip` — Gerbers y taladro comprimidos
- `fotometro.step` — modelo 3D de la placa
- `fotometro_pcb.pdf` / `.svg` — vistas de la placa en vectorial
- `fotometro_pcb_cara_superior.png`, `fotometro_pcb_cara_inferior.png`,
  `fotometro_vista3d_superior.png`, `fotometro_vista3d_perspectiva.png`, `fotometro_drc.png` — imágenes de las vistas y del DRC
- `fotometro_sch.pdf` / `fotometro_sch-1.png` — esquemático
- `BOM_fotometro.csv` — lista de materiales

Las bibliotecas propias están en `electronica/libraries/` y las hojas de datos
en `docs/datasheets/`. Los scripts que generan el esquemático y la PCB están en
`electronica/kicad/scripts/`.

## Autoría y uso de IA

Este repositorio fue preparado con ayuda de Claude (Anthropic) como asistente
de diseño: generación programática del esquemático y PCB en KiCad a partir
de la lista de materiales y topología de conexiones definidas por el
estudiante, además de la documentación. El detalle de este uso se describe
en `docs/informes/`, según lo pedido por el enunciado de la Parte II.

## Licencia

Este proyecto se publica bajo licencia MIT — ver [`LICENSE`](LICENSE).
