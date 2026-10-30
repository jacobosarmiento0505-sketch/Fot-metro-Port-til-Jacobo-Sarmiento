"""
Generador de PCB (version final, compacta) -- fotometro portatil.

Cambios respecto a v2:
  * Cada red se rutea como un ARBOL (cada pad nuevo se conecta al cobre mas
    cercano de su propia red, no a un pad fijo de una cadena).
  * Los pads duplicados de un mismo pin (p. ej. SW_PUSH_6mm) llevan la red en
    TODOS sus pads y cuentan como un unico terminal.
  * Las posiciones se pasan como parametro, para poder buscar una
    distribucion que sea realmente enrutable en una sola capa.
"""
import sys
import random
import math
import pcbnew

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router_astar import build_router, TRACK_W_MM

FPDIR = "/usr/share/kicad/footprints"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fotometro.kicad_pcb")

PH = ("Connector_PinHeader_2.54mm", "PinHeader_1x%02d_P2.54mm_Vertical")
RES = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
CD = ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm")
CP = ("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm")
PB = ("Button_Switch_THT", "SW_PUSH_6mm")
SS = ("Button_Switch_THT", "SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm")

# ref -> (lib, name, nets por pin)
PARTS = {
    "J1": (PH[0], PH[1] % 2, {"1": "BAT_RAW", "2": "GND"}),
    "SW1": (SS[0], SS[1], {"1": "BAT_RAW", "2": "VBAT_SW"}),
    "J2": (PH[0], PH[1] % 4, {"1": "VBAT_SW", "2": "GND", "3": "VCC_5V", "4": "GND"}),
    "J3": (PH[0], PH[1] % 7, {"1": "VCC_5V", "2": "GND", "3": "VCC_3V3", "4": "SDA",
                              "5": "SCL", "6": "GPIO_CAL", "7": "GPIO_MED"}),
    "J4": (PH[0], PH[1] % 4, {"1": "VCC_3V3", "2": "GND", "3": "SDA", "4": "SCL"}),
    "J5": (PH[0], PH[1] % 7, {"3": "SDA", "4": "SCL", "6": "GND", "7": "VCC_3V3"}),
    "R1": (RES[0], RES[1], {"1": "VCC_3V3", "2": "SDA"}),
    "R2": (RES[0], RES[1], {"1": "VCC_3V3", "2": "SCL"}),
    "SW2": (PB[0], PB[1], {"1": "GPIO_CAL", "2": "GND"}),
    "R3": (RES[0], RES[1], {"1": "VCC_3V3", "2": "GPIO_CAL"}),
    "C1": (CD[0], CD[1], {"1": "GPIO_CAL", "2": "GND"}),
    "SW3": (PB[0], PB[1], {"1": "GPIO_MED", "2": "GND"}),
    "R4": (RES[0], RES[1], {"1": "VCC_3V3", "2": "GPIO_MED"}),
    "C2": (CD[0], CD[1], {"1": "GPIO_MED", "2": "GND"}),
    "C3": (CP[0], CP[1], {"1": "VCC_3V3", "2": "GND"}),
    "C4": (CP[0], CP[1], {"1": "VCC_5V", "2": "GND"}),
    "C5": (CD[0], CD[1], {"1": "VCC_3V3", "2": "GND"}),
    "C6": (CD[0], CD[1], {"1": "VCC_3V3", "2": "GND"}),
    "C7": (CD[0], CD[1], {"1": "VCC_3V3", "2": "GND"}),
}

VALUES = {"J1": "Bateria Li-Po", "SW1": "Interruptor encendido", "J2": "TP4056+Boost5V", "J3": "ESP32",
          "J4": "OLED SSD1306", "J5": "TCS34725", "R1": "4.7k", "R2": "4.7k", "R3": "10k", "R4": "10k",
          "SW2": "CALIBRAR", "SW3": "MEDIR", "C1": "100nF", "C2": "100nF", "C3": "100uF", "C4": "100uF",
          "C5": "100nF", "C6": "100nF", "C7": "100nF"}

DEFAULT_PLACE = {
    "J1": (25, 25, 0), "SW1": (70, 25, 0), "J2": (115, 25, 0),
    "J3": (25, 75, 0), "J4": (70, 75, 0), "J5": (115, 75, 0),
    "R1": (20, 140, 0), "R2": (20, 160, 0),
    "SW2": (55, 140, 0), "R3": (55, 170, 0), "C1": (80, 140, 0),
    "SW3": (120, 140, 0), "R4": (120, 170, 0), "C2": (145, 140, 0),
    "C3": (20, 200, 0), "C4": (45, 200, 0), "C5": (70, 200, 0),
    "C6": (95, 200, 0), "C7": (120, 200, 0),
}


def build_board(place, W, H):
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = pcbnew.FromMM(0.8)
    ds.m_MinClearance = pcbnew.FromMM(0.8)
    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name, 0)
            board.Add(ni)
            nets[name] = board.FindNet(name)
        return nets[name]

    fps = {}
    for ref, (lib, name, pins) in PARTS.items():
        fp = pcbnew.FootprintLoad(f"{FPDIR}/{lib}.pretty", name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(VALUES.get(ref, ref))
        x, y, rot = place[ref]
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for p in fp.Pads():
            nm = pins.get(p.GetNumber(), "")
            if nm:
                p.SetNet(net(nm))
        fps[ref] = fp

    corners = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(4):
        (x1, y1), (x2, y2) = corners[i], corners[i + 1]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)

    for i, (hx, hy) in enumerate([(8, 8), (W - 8, 8), (8, H - 8), (W - 8, H - 8)]):
        mh = pcbnew.FootprintLoad(f"{FPDIR}/MountingHole.pretty", "MountingHole_3.2mm_M3")
        mh.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_3.2mm_M3"))
        mh.SetReference(f"MH{i+1}")
        mh.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
        board.Add(mh)
    return board, fps


FINAL_PLACE = {"J1": [74.48, 13.34, 270], "SW1": [89.61, 16.76, 90], "J2": [73.55, 19.03, 270], "J3": [54.4, 51.51, 0], "J4": [89.13, 34.93, 0], "J5": [92.98, 49.43, 90], "R1": [71.5, 37.76, 270], "R2": [80.14, 38.31, 270], "SW2": [86.62, 62.14, 0], "R3": [41.29, 48.11, 270], "C1": [81.34, 68.22, 90], "SW3": [18.34, 11.87, 0], "R4": [32.42, 52.02, 270], "C2": [11.4, 29.69, 0], "C3": [40.92, 37.48, 0], "C4": [45.68, 25.54, 0], "C5": [36.59, 27.72, 90], "C6": [29.0, 33.17, 180], "C7": [73.19, 28.58, 0]}
FINAL_W, FINAL_H = 120.8, 79.6
FINAL_ORDER = ['VCC_3V3', 'BAT_RAW', 'VBAT_SW', 'VCC_5V', 'GPIO_MED', 'SDA', 'GND', 'GPIO_CAL', 'SCL']
PRIORITY = list(FINAL_ORDER)
ALLOW_RELAXED = True


def route_board(board, fps, W, H, order_seed=0, verbose=False):
    router = build_router(board, W, H)
    astar_multi = router["astar_multi"]
    simplify = router["simplify"]
    commit_path = router["commit_path"]
    cell_to_mm = router["cell_to_mm"]
    mm_to_cell = router["mm_to_cell"]
    TRACK_W = pcbnew.FromMM(TRACK_W_MM)

    # terminales por red: (ref, pin) -> [posiciones mm de todos sus pads]
    net_terms = {}
    for ref, fp in fps.items():
        groups = {}
        for idx, p in enumerate(fp.Pads()):
            nm = p.GetNet().GetNetname()
            if not nm:
                continue
            # KiCad does NOT treat two pads that share a number as already
            # connected, so every physical pad is its own terminal.
            groups.setdefault((nm, f"{p.GetNumber()}#{idx}"), []).append(
                (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
        for (nm, num), poss in groups.items():
            net_terms.setdefault(nm, []).append(((ref, num), poss))

    rng = random.Random(order_seed)
    names = list(net_terms.keys())
    # orden base: redes con menos terminales primero; el seed lo perturba
    names.sort(key=lambda n: len(net_terms[n]))
    if order_seed:
        for i in range(len(names) - 1):
            if rng.random() < 0.4:
                j = rng.randrange(i, len(names))
                names[i], names[j] = names[j], names[i]

    names.sort(key=lambda n: (n not in PRIORITY, PRIORITY.index(n) if n in PRIORITY else 0))
    failures = []
    ntracks_before = len(list(board.GetTracks()))

    def draw(pts, net_item):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if (x1, y1) == (x2, y2):
                continue
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
            tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
            tr.SetWidth(TRACK_W)
            tr.SetLayer(pcbnew.B_Cu)
            tr.SetNet(net_item)
            board.Add(tr)

    for nm in names:
        terms = net_terms[nm]
        net_item = board.FindNet(nm)
        ncode = net_item.GetNetCode()
        if len(terms) < 2:
            continue
        # arbol inicial: terminal mas "central"
        cx = sum(p[0] for _, ps in terms for p in ps) / sum(len(ps) for _, ps in terms)
        cy = sum(p[1] for _, ps in terms for p in ps) / sum(len(ps) for _, ps in terms)
        terms = sorted(terms, key=lambda t: min((p[0]-cx)**2 + (p[1]-cy)**2 for p in t[1]))
        tree_cells = set()
        pad_exact = {}  # celda -> (x,y) exacto de un pad del arbol

        def add_term(ps):
            for (x, y) in ps:
                c = mm_to_cell(x, y)
                tree_cells.add(c)
                pad_exact[c] = (x, y)

        add_term(terms[0][1])
        remaining = list(terms[1:])
        while remaining:
            # el terminal restante mas cercano al arbol
            def dtree(t):
                return min(math.hypot(p[0]-q[0], p[1]-q[1])
                           for p in t[1] for q in pad_exact.values())
            remaining.sort(key=dtree)
            t = remaining.pop(0)
            done = False
            for ignore_soft in ((False, True) if ALLOW_RELAXED else (False,)):
                # probar cada pad del terminal, el mas cercano primero
                starts = sorted(t[1], key=lambda p: min(math.hypot(p[0]-q[0], p[1]-q[1])
                                                        for q in pad_exact.values()))
                for sp in starts:
                    path = astar_multi(sp, tree_cells, ncode, ignore_soft=ignore_soft)
                    if path is None:
                        continue
                    commit_path(path, ncode)
                    wp = [cell_to_mm(c) for c in simplify(path)]
                    end_cell = path[-1]
                    start_pt = sp
                    end_pt = pad_exact.get(end_cell, wp[-1])
                    pts = [start_pt] + wp[1:-1] + [end_pt]
                    draw(pts, net_item)
                    for c in path:
                        tree_cells.add(c)
                    add_term(t[1])
                    done = True
                    if verbose and ignore_soft:
                        print(f"   (margen relajado) {nm} {t[0]}")
                    break
                if done:
                    break
            if not done:
                failures.append((nm, t[0]))
                if verbose:
                    print(f"   !! SIN CAMINO: {nm} {t[0]}")
    return failures


def check_shorts(board):
    tracks = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_TRACK)]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    bad = []
    nets = lambda it: it.GetNet().GetNetCode()
    shp = [t.GetEffectiveShape() for t in tracks]
    for i in range(len(tracks)):
        for j in range(i + 1, len(tracks)):
            if nets(tracks[i]) != nets(tracks[j]) and shp[i].Collide(shp[j], 0):
                bad.append(("pista-pista", tracks[i].GetNet().GetNetname(), tracks[j].GetNet().GetNetname()))
    for i, t in enumerate(tracks):
        for p in pads:
            if nets(p) != nets(t) and shp[i].Collide(p.GetEffectiveShape(), 0):
                bad.append(("pista-pad", t.GetNet().GetNetname(), p.GetNet().GetNetname(),
                            p.GetParent().GetReference(), p.GetNumber()))
    return bad


def unconnected(board):
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(True)


def prune_stubs(board, max_len_mm=0.6):
    """Elimina tramos de pista muy cortos que no son necesarios para la conectividad."""
    base = unconnected(board)
    removed = 0
    for t in list(board.GetTracks()):
        if not isinstance(t, pcbnew.PCB_TRACK):
            continue
        if pcbnew.ToMM(t.GetLength()) < max_len_mm:
            board.Remove(t)
            if unconnected(board) > base:
                board.Add(t)
            else:
                removed += 1
    return removed


SHORT = {"GND": "G", "VCC_3V3": "3V3", "VCC_5V": "5V", "VBAT_SW": "VBAT", "BAT_RAW": "BAT+",
         "GPIO_MED": "MED", "GPIO_CAL": "CAL", "SDA": "SDA", "SCL": "SCL"}
NAMES = {"J1": "BATERIA", "SW1": "ON/OFF", "J2": "TP4056", "J3": "ESP32", "J4": "OLED", "J5": "TCS34725",
         "SW2": "CALIBRAR", "SW3": "MEDIR"}
TITLE = ["FOTOMETRO PORTATIL v2.0", "Electronica Ing. Biomedica - UDD", "Equipo 2 - Seccion 1",
         "J.Sarmiento S.Kotoras J.Otero"]


def _txt(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    t.SetTextAngleDegrees(rot)
    board.Add(t)
    return t


def add_silkscreen(board):
    """Nombre, version y equipo + funcion de conectores en F.SilkS (sin pisar footprints)."""
    f = 1e6
    boxes = {fp.GetReference(): fp.GetBoundingBox(True, False) for fp in board.GetFootprints()}
    taken = [(b.GetX() / f - 0.6, b.GetY() / f - 0.6, b.GetRight() / f + 0.6, b.GetBottom() / f + 0.6)
             for b in boxes.values()]
    bb = board.GetBoardEdgesBoundingBox()
    W, H = bb.GetWidth() / f, bb.GetHeight() / f

    def free(x0, y0, x1, y1):
        if x0 < 1 or y0 < 1 or x1 > W - 1 or y1 > H - 1:
            return False
        return all(x1 < a or x0 > c or y1 < b or y0 > d for a, b, c, d in taken)

    def place(s, size=1.0, rot=0, prefer=()):
        w = len(s) * size * 1.0
        h = size * 1.2
        cand = list(prefer)
        for y in range(2, int(H) - 2, 2):
            for x in range(2, int(W) - 2, 2):
                cand.append((x, y))
        for x, y in cand:
            x0, y0, x1, y1 = (x, y - h / 2, x + w, y + h / 2) if rot == 0 else (x - h / 2, y - w, x + h / 2, y)
            if free(x0, y0, x1, y1):
                taken.append((x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3))
                _txt(board, s, x, y, size, rot=rot)
                return True
        print('sin espacio para', s)
        return False

    for i, s in enumerate(TITLE):
        place(s, 1.2 if i == 0 else 1.0)
    # leyenda de pines (pin 1 = cuadrado) para cada conector
    legend = []
    for ref in ("J1", "J2", "J3", "J4", "J5"):
        nets = PARTS[ref][2]
        legend.append(ref + " " + NAMES[ref] + ": " + " ".join(f"{k}={SHORT.get(v, v)}" for k, v in sorted(nets.items(), key=lambda kv: int(kv[0]))) + "  (pin1 cuadrado)")
    for s in legend:
        place(s, 0.8)
    # nombre corto junto a cada modulo o pulsador
    for ref, s in NAMES.items():
        bx = boxes[ref]
        x0, y0, x1, y1 = bx.GetX() / f, bx.GetY() / f, bx.GetRight() / f, bx.GetBottom() / f
        pref = [(x0, y1 + 1.2), (x0, y0 - 1.2), (x1 + 1.0, (y0 + y1) / 2), (x0 - len(s) - 1.5, (y0 + y1) / 2)]
        place(s, 0.8, prefer=pref)


def run(place=None, W=175.0, H=220.0, order_seed=0, save=None, verbose=False):
    place = place or DEFAULT_PLACE
    board, fps = build_board(place, W, H)
    fails = route_board(board, fps, W, H, order_seed, verbose)
    print('tramos cortos eliminados:', prune_stubs(board))
    add_silkscreen(board)
    shorts = check_shorts(board)
    unc = unconnected(board)
    if save:
        board.Save(save)
    return board, fails, shorts, unc


if __name__ == "__main__":
    b, f, s, u = run(place=FINAL_PLACE, W=FINAL_W, H=FINAL_H, order_seed=0, save=OUT, verbose=True)
    print("sin ruta:", f)
    print("cortos:", len(s))
    print("sin conectar (KiCad):", u)
