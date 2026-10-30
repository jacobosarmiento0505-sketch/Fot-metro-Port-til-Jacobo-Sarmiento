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


FINAL_PLACE = {"J1": [72.31, 12.95, 270], "SW1": [87.0, 16.27, 90], "J2": [71.41, 18.48, 270], "J3": [52.82, 50.01, 0], "J4": [86.53, 33.91, 0], "J5": [90.27, 47.99, 90], "R1": [69.42, 36.66, 270], "R2": [77.81, 37.19, 270], "SW2": [84.1, 60.33, 0], "R3": [40.09, 46.71, 270], "C1": [78.97, 66.23, 90], "SW3": [17.81, 11.52, 0], "R4": [31.48, 50.5, 270], "C2": [11.07, 28.83, 0], "C3": [39.73, 36.39, 0], "C4": [44.35, 24.8, 0], "C5": [35.52, 26.91, 90], "C6": [28.16, 32.2, 180], "C7": [71.06, 27.75, 0]}
FINAL_W, FINAL_H = 117.3, 77.3
FINAL_ORDER = ['VBAT_SW', 'BAT_RAW', 'SDA', 'VCC_3V3', 'VCC_5V', 'GPIO_MED', 'GPIO_CAL', 'GND', 'SCL']
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


def run(place=None, W=175.0, H=220.0, order_seed=0, save=None, verbose=False):
    place = place or DEFAULT_PLACE
    board, fps = build_board(place, W, H)
    fails = route_board(board, fps, W, H, order_seed, verbose)
    print('tramos cortos eliminados:', prune_stubs(board))
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
