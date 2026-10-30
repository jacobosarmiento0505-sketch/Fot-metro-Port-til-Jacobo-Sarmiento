"""
Grid-based A* maze router for the single-layer (B.Cu) photometer PCB.

Instead of hand-tuned escape offsets (which kept producing new collisions
every time a different pair of nets happened to cross), this builds an
actual occupancy grid of the board and runs A* per connection, marking
cells as occupied by that net once routed so later connections route
around it. This is the standard "sequential maze router" approach and is
the correct fix for the class of problems we kept hitting (tracks skimming
sibling pads, tracks crossing other nets).
"""
import heapq
import math
import numpy as np
import pcbnew

RES_MM = 0.4                 # grid resolution
TRACK_W_MM = 0.8
TRACK_HALF_MM = TRACK_W_MM / 2
CLEARANCE_MM = 0.8

# HARD_MARGIN_MM is the minimum centerline-to-centerline distance that
# guarantees two DIFFERENT nets' copper can never physically touch/overlap,
# *regardless of clearance rules*. Each track has its own TRACK_HALF_MM of
# copper extending out from its centerline, so for net A's copper edge and
# net B's copper edge to not intersect, their centerlines must stay apart
# by at least (A's half width) + (B's half width) = TRACK_W_MM. Stamping
# the hard-obstacle halo with only TRACK_HALF_MM (as an earlier version of
# this file did) only accounts for the committing net's OWN half-width and
# not the crossing net's, which lets another net's path get as close as
# just past that halo -- well under the ~0.8mm actually needed -- and the
# two tracks' copper can end up genuinely overlapping (a real electrical
# short, confirmed by directly checking shape collisions on a generated
# board, not just relying on the DRC report). This is checked by `blocked()`
# even when ignore_soft=True, so it is the one guarantee that can never be
# relaxed.
HARD_MARGIN_MM = 1.2  # centro-a-centro minimo en modo relajado (hueco >= 0.4 mm)

# SOFT_MARGIN_MM is the normal-routing halo, which additionally reserves
# the DRC clearance rule's minimum gap (CLEARANCE_MM) beyond the hard
# no-overlap boundary -- this is what gives genuinely DRC-clean routing
# when a path isn't forced to fall back to the relaxed (ignore_soft) pass.
SOFT_MARGIN_MM = 1.6  # preferido: hueco de 0.8 mm (regla DRC)



def _claim(sub, mask, net_code):
    """Claim cells of `sub` (selected by boolean `mask`, or all cells if mask
    is None) for net_code. A free cell (-1) becomes net_code; a cell already
    held by the same net stays; a cell held by a DIFFERENT net becomes -2
    ("contested": inside the keep-out zone of two different nets at once),
    which blocked() treats as unusable for every net. Previously the first
    net to stamp a contested cell simply kept it, so that net could still
    route through a spot that was too close to the other net's pad (a real
    short when two pads sit only ~2 mm apart, as on the SW1 slide switch)."""
    if mask is None:
        mask = np.ones(sub.shape, dtype=bool)
    free = mask & (sub == -1)
    foreign = mask & (sub != -1) & (sub != net_code) & (sub != -2)
    sub[free] = net_code
    sub[foreign] = -2

def build_router(board, W_mm, H_mm, res_mm=RES_MM):
    nx = int(math.ceil(W_mm / res_mm)) + 1
    ny = int(math.ceil(H_mm / res_mm)) + 1
    hard_net = -1 * np.ones((ny, nx), dtype=np.int32)   # exact copper, net code (or -1)
    soft_net = -1 * np.ones((ny, nx), dtype=np.int32)   # clearance halo, net code (or -1)

    def mm_to_cell(x_mm, y_mm):
        return (int(round(x_mm / res_mm)), int(round(y_mm / res_mm)))

    def rect_cells(cx_mm, cy_mm, halfx_mm, halfy_mm, pad_mm=0.0):
        x0 = max(0, int(math.floor((cx_mm - halfx_mm - pad_mm) / res_mm)))
        x1 = min(nx - 1, int(math.ceil((cx_mm + halfx_mm + pad_mm) / res_mm)))
        y0 = max(0, int(math.floor((cy_mm - halfy_mm - pad_mm) / res_mm)))
        y1 = min(ny - 1, int(math.ceil((cy_mm + halfy_mm + pad_mm) / res_mm)))
        return x0, x1, y0, y1

    def stamp_pad(cx_mm, cy_mm, halfx_mm, halfy_mm, net_code):
        # A pad's hard-obstacle rect needs a TRACK_HALF_MM margin beyond its
        # exact copper outline too: unlike two tracks (where each side's own
        # half-width is already accounted for by HARD_MARGIN_MM), a pad has
        # no "half-width" of its own -- it's an exact shape -- so what has to
        # be reserved is just the crossing track's own half-width, so that
        # track's copper (centered on whatever cell it is allowed to use)
        # can never dip into the pad's exact footprint.
        x0, x1, y0, y1 = rect_cells(cx_mm, cy_mm, halfx_mm, halfy_mm, TRACK_HALF_MM + 0.4)
        _claim(hard_net[y0:y1 + 1, x0:x1 + 1], None, net_code)
        x0s, x1s, y0s, y1s = rect_cells(cx_mm, cy_mm, halfx_mm, halfy_mm, SOFT_MARGIN_MM)
        _claim(soft_net[y0s:y1s + 1, x0s:x1s + 1], None, net_code)

    def stamp_disk(cx_cell, cy_cell, radius_mm, net_code, target):
        # NOTE: the mask test below compares against radius_mm in real
        # millimetres (not grid-cell counts). An earlier version compared
        # squared *cell* distance against a cell-count radius; for a radius
        # of exactly 1 cell that silently excluded the diagonal neighbor
        # cells (true distance res_mm*sqrt(2) was being compared against a
        # cell-unit threshold of 1, not against the actual mm radius), so a
        # different net's path could land in a diagonal cell that was
        # geometrically closer than the intended exclusion radius -- one of
        # the causes of real copper-to-copper overlaps found when checking
        # the generated board directly.
        r_cells = max(1, int(math.ceil(radius_mm / res_mm)))
        x0 = max(0, cx_cell - r_cells)
        x1 = min(nx - 1, cx_cell + r_cells)
        y0 = max(0, cy_cell - r_cells)
        y1 = min(ny - 1, cy_cell + r_cells)
        yy, xx = np.ogrid[y0:y1 + 1, x0:x1 + 1]
        dist_mm2 = ((xx - cx_cell) * res_mm) ** 2 + ((yy - cy_cell) * res_mm) ** 2
        mask = dist_mm2 <= radius_mm ** 2
        sub = target[y0:y1 + 1, x0:x1 + 1]
        # CRITICAL: never let committing one net's path overwrite a cell
        # that a DIFFERENT net already claims (whether that's a pad stamped
        # at startup or a track committed earlier). An earlier version of
        # this function let hard_net writes overwrite unconditionally, which
        # meant a later track of net A, passing near a pad of net B, could
        # silently erase that pad's hard-obstacle halo and replace it with
        # net A's own code. A *subsequent* track of that SAME net A would
        # then see those cells as "already mine" (exempt from the blocked()
        # check) and could route straight through what should still have
        # been a permanently reserved no-go zone around net B's pad -- a
        # real copper-to-copper short, found by directly checking shape
        # collisions on the generated board. So both hard_net and soft_net
        # only ever claim a cell that is currently free (-1) or already
        # this same net; a cell already owned by a different net is left
        # exactly as it was.
        _claim(sub, mask, net_code)
        target[y0:y1 + 1, x0:x1 + 1] = sub

    # ---- stamp every pad of every footprint as an obstacle for OTHER nets --
    for fp in board.GetFootprints():
        for p in fp.Pads():
            pos = p.GetPosition()
            sz = p.GetSize()
            cx_mm = pcbnew.ToMM(pos.x)
            cy_mm = pcbnew.ToMM(pos.y)
            halfx_mm = pcbnew.ToMM(sz.x) / 2.0
            halfy_mm = pcbnew.ToMM(sz.y) / 2.0
            n = p.GetNet()
            ncode = n.GetNetCode() if n else 0
            stamp_pad(cx_mm, cy_mm, halfx_mm, halfy_mm, ncode)

    def blocked(cx, cy, net_code, ignore_soft=False):
        if cx < 0 or cx >= nx or cy < 0 or cy >= ny:
            return True
        h = hard_net[cy, cx]
        if h != -1 and h != net_code:
            return True
        if not ignore_soft:
            s = soft_net[cy, cx]
            if s != -1 and s != net_code:
                return True
        return False

    NEIGHBORS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                 (-1, -1, 1.41421356), (-1, 1, 1.41421356),
                 (1, -1, 1.41421356), (1, 1, 1.41421356)]

    def astar(start_mm, goal_mm, net_code, ignore_soft=False):
        sx, sy = mm_to_cell(*start_mm)
        gx, gy = mm_to_cell(*goal_mm)
        sx = min(max(sx, 0), nx - 1); sy = min(max(sy, 0), ny - 1)
        gx = min(max(gx, 0), nx - 1); gy = min(max(gy, 0), ny - 1)

        def h(x, y):
            return math.hypot(x - gx, y - gy)

        openq = [(h(sx, sy), 0.0, (sx, sy), None)]
        came = {}
        gscore = {(sx, sy): 0.0}
        visited = set()
        MAX_EXPANSIONS = 900000
        expansions = 0
        while openq:
            expansions += 1
            if expansions > MAX_EXPANSIONS:
                return None
            f, g, cur, parent = heapq.heappop(openq)
            if cur in visited:
                continue
            visited.add(cur)
            came[cur] = parent
            if cur == (gx, gy):
                # reconstruct
                path = []
                node = cur
                while node is not None:
                    path.append(node)
                    node = came[node]
                path.reverse()
                return path
            cx, cy = cur
            for dx, dy, cost in NEIGHBORS:
                nxx, nyy = cx + dx, cy + dy
                if (nxx, nyy) in visited:
                    continue
                # allow stepping onto the exact goal/start cell even if
                # blocked() would otherwise object (shouldn't happen since
                # pads of this net are exempted, but just in case)
                if (nxx, nyy) != (gx, gy) and blocked(nxx, nyy, net_code, ignore_soft):
                    continue
                if dx != 0 and dy != 0:
                    # avoid cutting a diagonal through two blocked orthogonal cells
                    if blocked(cx + dx, cy, net_code, ignore_soft) and blocked(cx, cy + dy, net_code, ignore_soft):
                        continue
                ng = g + cost
                if ng < gscore.get((nxx, nyy), 1e18):
                    gscore[(nxx, nyy)] = ng
                    heapq.heappush(openq, (ng + h(nxx, nyy), ng, (nxx, nyy), cur))
        return None

    def astar_multi(start_mm, goal_cells, net_code, ignore_soft=False):
        """A* from start to the NEAREST cell of goal_cells (any cell of the
        net's already-routed copper). Uses a Euclidean distance transform of
        the goal set as the heuristic (admissible, O(1) lookup)."""
        from scipy.ndimage import distance_transform_edt
        sx, sy = mm_to_cell(*start_mm)
        sx = min(max(sx, 0), nx - 1); sy = min(max(sy, 0), ny - 1)
        goalset = set(goal_cells)
        if not goalset:
            return None
        mask = np.zeros((ny, nx), dtype=bool)
        for (gx, gy) in goalset:
            mask[gy, gx] = True
        dist = distance_transform_edt(~mask)
        openq = [(float(dist[sy, sx]), 0.0, (sx, sy), None)]
        came = {}
        gscore = {(sx, sy): 0.0}
        visited = set()
        expansions = 0
        while openq:
            expansions += 1
            if expansions > 200000:
                return None
            f, g, cur, parent = heapq.heappop(openq)
            if cur in visited:
                continue
            visited.add(cur)
            came[cur] = parent
            if cur in goalset:
                path = []
                node = cur
                while node is not None:
                    path.append(node)
                    node = came[node]
                path.reverse()
                return path
            cx, cy = cur
            for dx, dy, cost in NEIGHBORS:
                nxx, nyy = cx + dx, cy + dy
                if (nxx, nyy) in visited:
                    continue
                if (nxx, nyy) not in goalset and blocked(nxx, nyy, net_code, ignore_soft):
                    continue
                if dx != 0 and dy != 0:
                    if blocked(cx + dx, cy, net_code, ignore_soft) and blocked(cx, cy + dy, net_code, ignore_soft):
                        continue
                ng = g + cost
                if ng < gscore.get((nxx, nyy), 1e18):
                    gscore[(nxx, nyy)] = ng
                    heapq.heappush(openq, (ng + float(dist[nyy, nxx]), ng, (nxx, nyy), cur))
        return None

    def simplify(path_cells):
        """Collapse collinear runs into key waypoints."""
        if not path_cells:
            return []
        pts = [path_cells[0]]
        for i in range(1, len(path_cells) - 1):
            x0, y0 = path_cells[i - 1]
            x1, y1 = path_cells[i]
            x2, y2 = path_cells[i + 1]
            d1 = (x1 - x0, y1 - y0)
            d2 = (x2 - x1, y2 - y1)
            if d1 != d2:
                pts.append(path_cells[i])
        pts.append(path_cells[-1])
        return pts

    def commit_path(path_cells, net_code):
        for (cx, cy) in path_cells:
            stamp_disk(cx, cy, HARD_MARGIN_MM, net_code, hard_net)
            stamp_disk(cx, cy, SOFT_MARGIN_MM, net_code, soft_net)

    def cell_to_mm(c):
        return (c[0] * res_mm, c[1] * res_mm)

    def blocked_debug(x_mm, y_mm, net_code, ignore_soft=False):
        cx, cy = mm_to_cell(x_mm, y_mm)
        return blocked(cx, cy, net_code, ignore_soft), hard_net[cy, cx], soft_net[cy, cx]

    return {
        "astar": astar,
        "astar_multi": astar_multi,
        "simplify": simplify,
        "commit_path": commit_path,
        "cell_to_mm": cell_to_mm,
        "mm_to_cell": mm_to_cell,
        "blocked_debug": blocked_debug,
    }
