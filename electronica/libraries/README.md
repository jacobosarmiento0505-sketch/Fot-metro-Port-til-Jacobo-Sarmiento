# Bibliotecas del proyecto

Estas bibliotecas permiten abrir el proyecto desde otro computador sin
depender de archivos locales (se enlazan en `electronica/kicad/sym-lib-table` y
`electronica/kicad/fp-lib-table` con la ruta `${KIPRJMOD}/../libraries/`).

## Símbolos (`fotometro_custom.kicad_sym`)

| Símbolo | Origen | Qué se cambió | Verificación |
|---|---|---|---|
| `SW_SPDT_COM1` | `Switch:SW_SPDT` de KiCad | Pines 1 y 2 intercambiados para que el pin 1 sea el común, igual que el pad 1 (centro) del footprint Würth WS-SLTV | 3 pines, numeración = footprint |
| `VCC_3V3` | `power:VCC` | Nombre de pin/valor cambiado a `VCC_3V3` para tener un riel separado | red `VCC_3V3` en el netlist |
| `VCC_5V` | `power:VCC` | Nombre de pin/valor cambiado a `VCC_5V` | red `VCC_5V` en el netlist |

## Footprints (`*.pretty`)

Copias locales, sin modificar, de las bibliotecas oficiales de KiCad
(`Connector_PinHeader_2.54mm`, `Button_Switch_THT`, `Resistor_THT`,
`Capacitor_THT`, `MountingHole`) con solo los footprints usados, y enlazadas
en `kicad/fp-lib-table` con `${KIPRJMOD}`; así el proyecto abre igual en
cualquier computador y versión de KiCad. Footprints usados:
`PinHeader_1x02/1x04/1x07_P2.54mm_Vertical`,
`SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm` (pitch 2,54 mm; el de 2 mm
original impedía cumplir los 0,8 mm de separación), `SW_PUSH_6mm`,
`R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal`,
`C_Disc_D5.0mm_W2.5mm_P5.00mm`, `CP_Radial_D6.3mm_P2.50mm` y
`MountingHole_3.2mm_M3` (agujero de 3,2 mm).

Fuente: <https://gitlab.com/kicad/libraries/kicad-footprints> (CC-BY-SA 4.0 con excepción).

## Modelos 3D

El archivo `outputs/fotometro.step` contiene la placa y los componentes que
tienen modelo 3D en las bibliotecas oficiales de KiCad.
