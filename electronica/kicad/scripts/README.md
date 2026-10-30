# Scripts de generación

Scripts usados para generar el esquemático y el PCB de este proyecto de
forma programática (vía las APIs `kiutils` y `pcbnew` de Python de KiCad),
incluidos por trazabilidad. No son necesarios para abrir o editar el
proyecto — eso se hace directamente en la interfaz de KiCad con los
archivos `.kicad_sch` / `.kicad_pcb` de la carpeta de arriba.

- `gen_schematic.py` — genera `fotometro.kicad_sch` a partir de la lista de
  componentes y la topología de conexiones del circuito.
- `gen_pcb.py` — coloca los footprints (distribución compacta final, encontrada con una búsqueda automática) en la PCB y enruta las pistas; reproduce exactamente `fotometro.kicad_pcb`.
- `router_astar.py` — router de pistas usado por `gen_pcb.py`: construye
  una grilla de ocupación del PCB y usa búsqueda A* para encontrar, para
  cada conexión, un camino que evite los demás componentes y las pistas ya
  dibujadas, garantizando siempre que el cobre de redes distintas nunca se
  toque. Intenta primero el margen completo de 0.8 mm y, si no hay camino,
  usa un margen reducido (hueco mínimo 0.4 mm): ese es el origen de los
  avisos de clearance del DRC (ver el `README.md` principal).
