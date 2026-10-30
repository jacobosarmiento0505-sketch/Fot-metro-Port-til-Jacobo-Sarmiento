"""Generador del esquemático CABLEADO del Fotómetro portátil (KiCad 7+ / kiutils).

Cambios v2 (retroalimentación del profesor):
  * textos / títulos de bloque / descripciones de pines para reconocer cada componente
  * botones SW2 / SW3 cableados con alambres reales (pull-up + nodo + pulsador + C a GND)
  * ESP32 (J3) con TODOS sus pines cableados (alimentación con símbolos de potencia,
    SDA/SCL como buses hacia J4, J5 y los pull-ups, GPIO hacia los botones)
"""
import os
import uuid as uuidlib
from kiutils.schematic import (Schematic, SchematicSymbol, Property, LocalLabel,
                               HierarchicalSheetInstance, SymbolProjectInstance,
                               SymbolProjectPath, NoConnect)
from kiutils.symbol import SymbolLib
from kiutils.items.common import (Position, Effects, Font, Justify, Stroke,
                                  TitleBlock, PageSettings)
from kiutils.items.schitems import Connection, Junction, Text, Rectangle
from kiutils.items.common import Fill

SYMDIR = "/usr/share/kicad/symbols"
PROJECT_NAME = "fotometro-portatil"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fotometro.kicad_sch")


def new_uuid():
    return str(uuidlib.uuid4())


lib_cache = {}


def get_libsym(libname, entry):
    key = f"{libname}:{entry}"
    if key not in lib_cache:
        lib = SymbolLib().from_file(f"{SYMDIR}/{libname}.kicad_sym")
        s = next(x for x in lib.symbols if x.entryName == entry)
        s.libraryNickname = libname
        lib_cache[key] = s
    return lib_cache[key]


def _custom_spdt():
    """SW_SPDT con numeracion de la huella Wuerth: pin 1 = comun (centro), pin 2 = contacto A"""
    import copy
    b = copy.deepcopy(get_libsym("Switch", "SW_SPDT"))
    b.entryName = "SW_SPDT_COM1"
    for prop in b.properties:
        if prop.key == "Value":
            prop.value = "SW_SPDT_COM1"
    for u in b.units:
        u.entryName = "SW_SPDT_COM1"
        for pn in u.pins:
            pn.number = {"1": "2", "2": "1"}.get(pn.number, pn.number)
    lib_cache["Switch:SW_SPDT_COM1"] = b


def pin_local(libname, entry):
    s = get_libsym(libname, entry)
    return {p.number: (p.position.X, p.position.Y) for u in s.units for p in u.pins}


sch = Schematic().create_new()
sch.version = "20230121"
sch.uuid = new_uuid()
sch.paper = PageSettings(paperSize="A3")
sch.titleBlock = TitleBlock(
    title="Fotómetro portátil para análisis de muestras",
    date="2026-10-23", revision="2.0",
    company="Universidad del Desarrollo (UDD) - Ingeniería Civil Biomédica",
    comments={1: "Electrónica para Ingeniería Biomédica - Parte II",
              2: "Autor: Jacobo Sarmiento Espinosa",
              3: "Placa de integración: ESP32 + OLED + TCS34725 + TP4056/Boost"})
root_path = f"/{sch.uuid}"
placed_lib_ids = set()
GLOBAL_PINS = {}      # (ref, pin) -> (x, y)

R2 = lambda v: round(v + 0.0, 2)


# ------------------------------------------------------------------ primitivas
def eff(size=1.27, bold=False, hide=False, h=None, v=None):
    e = Effects(font=Font(height=size, width=size, bold=bold),
                justify=Justify(horizontally=h, vertically=v))
    e.hide = hide
    return e


def wire(*pts):
    for a, b in zip(pts[:-1], pts[1:]):
        c = Connection(type="wire",
                       points=[Position(X=R2(a[0]), Y=R2(a[1])),
                               Position(X=R2(b[0]), Y=R2(b[1]))],
                       stroke=Stroke(width=0, type="default"))
        c.uuid = new_uuid()
        sch.graphicalItems.append(c)


def junction(p):
    j = Junction(position=Position(X=R2(p[0]), Y=R2(p[1])), diameter=0)
    j.uuid = new_uuid()
    sch.junctions.append(j)


def nc(p):
    n = NoConnect()
    n.position = Position(X=R2(p[0]), Y=R2(p[1]))
    n.uuid = new_uuid()
    sch.noConnects.append(n)


def label(text, p, angle=0):
    l = LocalLabel()
    l.text = text
    l.position = Position(X=R2(p[0]), Y=R2(p[1]), angle=angle)
    l.effects = eff(1.27)
    l.uuid = new_uuid()
    sch.labels.append(l)


def note(text, x, y, size=1.5, bold=False, h="left"):
    t = Text(text=text, position=Position(X=R2(x), Y=R2(y), angle=0),
             effects=eff(size, bold=bold, h=h))
    t.uuid = new_uuid()
    sch.texts.append(t)


def frame(x1, y1, x2, y2):
    r = Rectangle(start=Position(X=x1, Y=y1), end=Position(X=x2, Y=y2),
                  stroke=Stroke(width=0.3, type="dash"), fill=Fill(type="none"))
    r.uuid = new_uuid()
    sch.shapes.append(r)


def transform(lx, ly, mirror, angle):
    """punto local (y hacia arriba) -> offset global (y hacia abajo)"""
    import math
    if mirror == "y":
        lx = -lx
    if mirror == "x":
        ly = -ly
    a = math.radians(angle)
    rx = lx * math.cos(a) - ly * math.sin(a)
    ry = lx * math.sin(a) + ly * math.cos(a)
    return rx, -ry


def _add_symbol(ref, libname, entry, value, footprint, x, y, mirror, angle,
                ref_at, val_at, hide_ref=False, hide_val=False, in_bom=True):
    lib_id = f"{libname}:{entry}"
    if lib_id not in placed_lib_ids:
        sch.libSymbols.append(get_libsym(libname, entry))
        placed_lib_ids.add(lib_id)
    inst = SchematicSymbol()
    inst.libId = lib_id
    inst.position = Position(X=R2(x), Y=R2(y), angle=angle)
    inst.mirror = mirror
    inst.unit = 1
    inst.inBom = in_bom
    inst.onBoard = in_bom
    inst.uuid = new_uuid()

    def prop(key, val, at, hide=False):
        p = Property(key=key, value=val)
        h = at[2] if len(at) > 2 else None
        p.position = Position(X=R2(at[0]), Y=R2(at[1]), angle=(360 - angle) % 360)
        p.effects = eff(1.27, hide=hide, h=h)
        return p

    props = [prop("Reference", ref, ref_at, hide_ref),
             prop("Value", value, val_at, hide_val)]
    if footprint:
        props.append(prop("Footprint", footprint, (x, y), True))
    inst.properties = props
    spp = SymbolProjectPath(sheetInstancePath=root_path, reference=ref, unit=1)
    inst.instances = [SymbolProjectInstance(name=PROJECT_NAME, paths=[spp])]
    sch.schematicSymbols.append(inst)
    for num, (lx, ly) in pin_local(libname, entry).items():
        dx, dy = transform(lx, ly, mirror, angle)
        GLOBAL_PINS[(ref, num)] = (R2(x + dx), R2(y + dy))


def comp(ref, libname, entry, value, footprint, x, y, mirror=None, angle=0,
         ref_at=None, val_at=None):
    ref_at = ref_at or (x + 3, y - 2.5, "left")
    val_at = val_at or (x + 3, y + 2.5, "left")
    _add_symbol(ref, libname, entry, value, footprint, x, y, mirror, angle,
                ref_at, val_at)


def P(ref, pin):
    return GLOBAL_PINS[(ref, str(pin))]


_pwr_count = [0]
_flg_count = [0]
ANGLE = {("GND", "down"): 0, ("GND", "right"): 90, ("GND", "left"): 270,
         ("VCC", "up"): 0, ("VCC", "left"): 90, ("VCC", "right"): 270,
         ("VCC", "down"): 180}


def _custom_vcc(net):
    import copy
    lid = f"power:{net}"
    if lid not in lib_cache_names:
        base = copy.deepcopy(get_libsym("power", "VCC"))
        base.entryName = net
        for prop in base.properties:
            if prop.key == "Value":
                prop.value = net
        for u in base.units:
            u.entryName = net
            for pn in u.pins:
                pn.name = net
        lib_cache[f"power:{net}"] = base
        lib_cache_names.add(lid)
    return net


lib_cache_names = set()


def pwr(net, p, side):
    """símbolo de potencia (VCC/GND) con su pin en el punto p; el cuerpo apunta a 'side'"""
    kind = "GND" if net == "GND" else _custom_vcc(net)
    _pwr_count[0] += 1
    ang = ANGLE[("GND" if net == "GND" else "VCC", side)]
    ox, oy = {"up": (0, -3.6), "down": (0, 4.2), "left": (-3.9, 0), "right": (3.9, 0)}[side]
    hj = {"left": "right", "right": "left"}.get(side)
    _add_symbol(f"#PWR{_pwr_count[0]:02d}", "power", kind, net, None,
                p[0], p[1], None, ang,
                (p[0], p[1] - 6), (p[0] + ox, p[1] + oy, hj),
                hide_ref=True, in_bom=False)
    # el texto del Value debe ir centrado en vertical
    inst = sch.schematicSymbols[-1]
    inst.properties[1].effects.justify.vertically = None


def pwr_flag(p):
    _flg_count[0] += 1
    _add_symbol(f"#FLG{_flg_count[0]:02d}", "power", "PWR_FLAG", "PWR_FLAG", None,
                p[0], p[1], None, 0, (p[0], p[1] - 4), (p[0], p[1] - 2.5),
                hide_ref=True, hide_val=True, in_bom=False)


# ------------------------------------------------------------------ footprints
FP_H1 = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_H4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_H7 = "Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical"
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_CP = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
FP_PB = "Button_Switch_THT:SW_PUSH_6mm"
FP_SW = "Button_Switch_THT:SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm"

# =============================================================== TÍTULO GENERAL
note("FOTÓMETRO PORTÁTIL - ESQUEMÁTICO ELÉCTRICO (placa de integración)", 20, 16, 3.5, True)
note("Todas las conexiones están cableadas. Los nombres de red (VCC_3V3, VCC_5V, GND, SDA, SCL, ...) "
     "coinciden con los de la PCB.", 20, 22, 1.5)

# =============================================================== 1. ALIMENTACIÓN
frame(15, 28, 200, 80)
note("1. ALIMENTACIÓN: batería Li-Po -> interruptor -> módulo TP4056 + Boost 5 V", 18, 33, 2.2, True)

comp("J1", "Connector_Generic", "Conn_01x02", "Batería Li-Po", FP_H1, 63.5, 50.8,
     mirror="y", ref_at=(63.5, 44, None), val_at=(63.5, 46.5, None))
_custom_spdt()
comp("SW1", "Switch", "SW_SPDT_COM1", "Interruptor encendido", FP_SW, 111.76, 50.8,
     ref_at=(111.76, 42, None), val_at=(111.76, 44.5, None))
comp("J2", "Connector_Generic", "Conn_01x04", "Carga+Regulador TP4056+Boost5V", FP_H4, 165.1, 50.8,
     ref_at=(172, 44, "left"), val_at=(172, 46.5, "left"))

wire(P("J1", 1), P("SW1", 1))
label("BAT_RAW", (85.0, 50.8))
wire(P("SW1", 2), P("J2", 1))
label("VBAT_SW", (135.0, 48.26))
nc(P("SW1", 3))
# J1 pin 2 -> GND
s = P("J1", 2)
wire(s, (s[0] + 5.08, s[1]))
pwr("GND", (s[0] + 5.08, s[1]), "right")
# J2: pines 2,3,4
for pin, net in ((2, "GND"), (3, "VCC_5V"), (4, "GND")):
    q = P("J2", pin)
    wire(q, (q[0] - 5.08, q[1]))
    pwr(net, (q[0] - 5.08, q[1]), "left")

note("J1: batería Li-Po 3.7 V", 40, 56, 1.27, h="left")
note("(pin 1 = +, pin 2 = -)", 40, 58.5, 1.27, h="left")
note("SW1: ON / OFF", 100, 60, 1.27, h="left")
note("J2 pin 1: entrada batería (B+)", 140, 63, 1.27, h="left")
note("J2 pin 2/4: GND   pin 3: salida 5 V", 140, 65.5, 1.27, h="left")
note("Salida del módulo: VCC_5V (alimenta al ESP32)", 140, 68, 1.27, h="left")

# =============================================================== 2. ESP32 + I2C
frame(15, 88, 335, 176)
note("2. CONTROL: ESP32 (J3) y bus I2C (OLED J4, sensor de color J5)", 18, 93, 2.2, True)

comp("J3", "Connector_Generic", "Conn_01x07", "ESP32 (dev board)", FP_H7, 63.5, 152.4,
     mirror="y", ref_at=(63.5, 138.5, None), val_at=(63.5, 136, None))
comp("J4", "Connector_Generic", "Conn_01x04", "OLED SSD1306 I2C", FP_H4, 137.16, 114.3,
     ref_at=(141.5, 111.76, "left"), val_at=(141.5, 114.3, "left"))
comp("J5", "Connector_Generic", "Conn_01x07", "TCS34725 HW-393 I2C", FP_H7, 137.16, 142.24,
     ref_at=(141.5, 137.2, "left"), val_at=(141.5, 139.7, "left"))
comp("R1", "Device", "R", "4.7k", FP_R, 96.52, 107.95, ref_at=(94.4, 106.7, "right"),
     val_at=(94.4, 109.3, "right"))
comp("R2", "Device", "R", "4.7k", FP_R, 109.22, 107.95, ref_at=(111.4, 106.7, "left"),
     val_at=(111.4, 109.3, "left"))

# descripción de pines J3 (a la izquierda del símbolo)
for pin, txt in ((1, "1  VIN 5 V"), (2, "2  GND"), (3, "3  3V3 (salida regulada)"),
                 (4, "4  SDA (I2C)"), (5, "5  SCL (I2C)"),
                 (6, "6  Botón CALIBRAR"), (7, "7  Botón MEDIR")):
    q = P("J3", pin)
    note(txt, 59.5, q[1] + 0.5, 1.27, h="right")

# J3 alimentación (pines 1..3)
for pin, net in ((1, "VCC_5V"), (2, "GND"), (3, "VCC_3V3")):
    q = P("J3", pin)
    e = (q[0] + 5.08, q[1])
    wire(q, e)
    pwr(net, e, "right")

# buses I2C
SDA_X, SCL_X, Y_P = 96.52, 109.22, 111.76
q4, q5 = P("J3", 4), P("J3", 5)
wire(q4, (SDA_X, q4[1]))
TAPS = {"SDA": sorted([P("J4", 3)[1], P("J5", 3)[1]]), "SCL": sorted([P("J4", 4)[1], P("J5", 4)[1]])}
def bus(x, y0, taps, ytop):
    ys = [y0] + sorted(taps, reverse=True) + [ytop]
    for a, b in zip(ys[:-1], ys[1:]):
        wire((x, a), (x, b))
bus(SDA_X, q4[1], TAPS["SDA"], Y_P)
wire(q5, (SCL_X, q5[1]))
bus(SCL_X, q5[1], TAPS["SCL"], Y_P)
label("SDA", (86.0, q4[1]))
label("SCL", (101.6, q5[1]))

# pull-ups (pin 2 sobre el extremo del bus, pin 1 a VCC_3V3)
assert P("R1", 2) == (SDA_X, Y_P) and P("R2", 2) == (SCL_X, Y_P), (P("R1", 2), P("R2", 2))
pwr("VCC_3V3", P("R1", 1), "up")
pwr("VCC_3V3", P("R2", 1), "up")

# derivaciones a J4 y J5
for dev in ("J4", "J5"):
    sda, scl = P(dev, 3), P(dev, 4)
    wire((SDA_X, sda[1]), sda)
    junction((SDA_X, sda[1]))
    wire((SCL_X, scl[1]), scl)
    junction((SCL_X, scl[1]))

# alimentación de J4
for pin, net in ((1, "VCC_3V3"), (2, "GND")):
    q = P("J4", pin)
    wire(q, (q[0] - 5.08, q[1]))
    pwr(net, (q[0] - 5.08, q[1]), "left")
# alimentación de J5 y NC
for pin, net in ((6, "GND"), (7, "VCC_3V3")):
    q = P("J5", pin)
    wire(q, (q[0] - 5.08, q[1]))
    pwr(net, (q[0] - 5.08, q[1]), "left")
for pin in (1, 2, 5):
    nc(P("J5", pin))

note("J4: pantalla OLED SSD1306", 145, 120.5, 1.27, h="left")
note("pin 1 VCC  2 GND  3 SDA  4 SCL", 145, 123, 1.27, h="left")
note("J5: sensor de color TCS34725 (HW-393)", 145, 152, 1.27, h="left")
note("pin 3 SDA  4 SCL  6 GND  7 VCC", 145, 154.5, 1.27, h="left")
note("pines 1, 2, 5 sin conexión (NC)", 145, 157, 1.27, h="left")
note("R1, R2: pull-up 4.7 k del bus I2C", 125, 100, 1.27, h="left")

# =============================================================== 3. BOTONES
frame(15, 180, 200, 252)
note("3. BOTONES: pull-up 10 k + antirrebote 100 nF", 90, 185, 2.2, True)


def boton(n_sw, n_r, n_c, texto, net, ypin_j3, vx, yn):
    """circuito idéntico al ejemplo del profesor: R a VCC_3V3, nodo (unión) en la línea del GPIO,
       pulsador al nodo y a GND, condensador del nodo a GND."""
    XR, XC, XS = 114.3, 139.7, 165.1
    comp(n_r, "Device", "R", "10k", FP_R, XR, yn - 3.81, ref_at=(XR - 2.2, yn - 5.1, "right"),
         val_at=(XR - 2.2, yn - 2.6, "right"))
    comp(n_c, "Device", "C", "100nF", FP_C, XC, yn + 3.81, ref_at=(XC + 2.2, yn + 2.5, "left"),
         val_at=(XC + 2.2, yn + 5.1, "left"))
    comp(n_sw, "Switch", "SW_Push", texto, FP_PB, XS, yn,
         ref_at=(XS, yn - 5.5, None), val_at=(XS, yn - 3, None))
    j3 = P("J3", ypin_j3)
    wire(j3, (vx, j3[1]))
    wire((vx, j3[1]), (vx, yn))
    wire((vx, yn), P(n_r, 2))
    label(net, (vx + 8, yn))
    pwr("VCC_3V3", P(n_r, 1), "up")
    node = P(n_r, 2)
    junction(node)
    wire(node, P(n_c, 1))
    junction(P(n_c, 1))
    wire(P(n_c, 1), P(n_sw, 1))
    pwr("GND", P(n_c, 2), "down")
    s2 = P(n_sw, 2)
    wire(s2, (s2[0], s2[1] + 5.08))
    pwr("GND", (s2[0], s2[1] + 5.08), "down")
    note(f"{n_sw}: pulsador {texto}", XS + 8, yn + 1.0, 1.27, h="left")
    note("(al pulsar: GPIO = GND)", XS + 8, yn + 3.5, 1.27, h="left")
    note(f"{n_r}: pull-up 10 k a 3V3", XR - 8, yn + 6.5, 1.27, h="left")
    note(f"{n_c}: antirrebote 100 nF", XC - 6, yn + 12, 1.27, h="left")


boton("SW2", "R3", "C1", "CALIBRAR", "GPIO_CAL", 6, 83.82, 207.0)
boton("SW3", "R4", "C2", "MEDIR", "GPIO_MED", 7, 76.2, 238.76)

# =============================================================== 4. DESACOPLE
frame(205, 180, 335, 252)
note("4. DESACOPLE de alimentación", 208, 185, 2.2, True)
XS0, YC = 228.6, 210.82
caps = [("C3", "100uF", "VCC_3V3", True), ("C5", "100nF", "VCC_3V3", False),
        ("C6", "100nF", "VCC_3V3", False), ("C7", "100nF", "VCC_3V3", False),
        ("C4", "100uF", "VCC_5V", True)]
for i, (ref, val, net, pol) in enumerate(caps):
    x = XS0 + i * 22.86
    if pol:
        comp(ref, "Device", "C_Polarized", val, FP_CP, x, YC, ref_at=(x - 2.5, YC - 1.5, "right"),
             val_at=(x - 2.5, YC + 1.5, "right"))
    else:
        comp(ref, "Device", "C", val, FP_C, x, YC, ref_at=(x - 2.5, YC - 1.5, "right"),
             val_at=(x - 2.5, YC + 1.5, "right"))
    top, bot = P(ref, 1), P(ref, 2)
    pwr(net, top, "up")
    pwr("GND", bot, "down")
    if ref in ("C3", "C4"):         # PWR_FLAG: la red es alimentada por conectores pasivos
        junction(top)
        wire(top, (top[0] + 5.08, top[1]))
        pwr_flag((top[0] + 5.08, top[1]))
    if ref == "C3":
        junction(bot)
        wire(bot, (bot[0] + 5.08, bot[1]))
        pwr_flag((bot[0] + 5.08, bot[1]))
note("C3, C4: electrolíticos 100 uF (reserva de energía 3V3 / 5V)", 208, 233, 1.27, h="left")
note("C5, C6, C7: 100 nF cerámicos, uno por módulo (J3, J4, J5)", 208, 236, 1.27, h="left")

# =============================================================== LEYENDA
note("LEYENDA DE REDES", 215, 30, 1.8, True)
for i, t in enumerate(["VCC_5V : salida 5 V del módulo TP4056 + Boost",
                       "VCC_3V3 : 3.3 V regulados del ESP32",
                       "BAT_RAW / VBAT_SW : batería antes / después del interruptor",
                       "SDA, SCL : bus I2C (OLED + TCS34725)",
                       "GPIO_CAL, GPIO_MED : entradas de los botones (activas en bajo)"]):
    note(t, 215, 36 + i * 4, 1.27, h="left")

shi = HierarchicalSheetInstance()
shi.path = "/"
shi.page = "1"
sch.sheetInstances = [shi]

sch.to_file(OUT)
print("Schematic written:", OUT)
print("Symbols:", len(sch.schematicSymbols), "wires:", len([g for g in sch.graphicalItems]),
      "junctions:", len(sch.junctions), "texts:", len(sch.texts))
