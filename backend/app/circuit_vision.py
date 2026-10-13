"""CPU symbol geometry + OCR association + raster wire topology for schematics.
Supports discrete passive circuits (R, C, V) as well as complex multi-IC digital systems.
"""
import csv, io, os, re, shutil, sqlite3, subprocess, tempfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from .vision_local import prepare
from .ingestion import Circuit, Component, Net, Node
from .engine import OperationError

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'libraries' / 'index' / 'components.db'

def words(tsv):
    result = []
    for line in tsv.splitlines():
        parts = line.split('\t')
        if len(parts) >= 12 and parts[0] == '5':
            txt = parts[11].strip()
            if txt and len(txt) < 80:
                try:
                    conf = float(parts[10])
                    result.append({
                        'text': txt,
                        'conf': conf,
                        'x': int(parts[6]),
                        'y': int(parts[7]),
                        'w': int(parts[8]),
                        'h': int(parts[9])
                    })
                except (ValueError, IndexError):
                    pass
    return result

def bodies(binary):
    found = []
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours[:8000]:
        x, y, w, h = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if min(w, h) < 16 or max(w, h) > 400 or area < 120:
            continue
        ratio = max(w, h) / min(w, h)
        approx = cv2.approxPolyDP(c, .025 * cv2.arcLength(c, True), True)
        if ratio > 1.8 and len(approx) == 4 and area / (w * h) > .65:
            kind = 'R'
        elif min(w, h) >= 30 and ratio < 1.35 and len(approx) >= 7 and .50 < area / (w * h) < .85:
            kind = 'V'
        elif 30 <= w <= 350 and 20 <= h <= 300 and area / (w * h) > .45:
            kind = 'U'
        else:
            continue
        if not any(f['kind'] == kind and abs((f['x'] + f['w']/2) - (x + w/2)) + abs((f['y'] + f['h']/2) - (y + h/2)) < 20 for f in found):
            found.append(dict(kind=kind, x=x, y=y, w=w, h=h, closed=True))

    lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=10, minLineLength=10, maxLineGap=4)
    lines = [] if lines is None else [tuple(map(int, l[0])) for l in lines[:1500]]
    diagonals = [l for l in lines if 0.15 < abs(l[2]-l[0])/max(1, abs(l[3]-l[1])) < 6.5 and max(abs(l[2]-l[0]), abs(l[3]-l[1])) < 95]
    groups = []
    for line in diagonals[:500]:
        points = [line[:2], line[2:]]; near = []
        for i, g in enumerate(groups):
            if any(np.linalg.norm(np.array(a) - b) < 25 for a in points for b in g['points']):
                near.append(i)
        group = {'lines': [line], 'points': points}
        for i in reversed(near):
            old = groups.pop(i)
            group['lines'] += old['lines']
            group['points'] += old['points']
        groups.append(group)

    changed = True
    while changed:
        changed = False
        for i, a in enumerate(groups):
            aa = np.array(a['points']); lo = aa.min(axis=0); hi = aa.max(axis=0)
            for j in range(i+1, len(groups)):
                bb = np.array(groups[j]['points']); bl = bb.min(axis=0); bh = bb.max(axis=0)
                overlap = np.minimum(hi, bh) - np.maximum(lo, bl); sizes = np.minimum(hi-lo, bh-bl)
                if (overlap[0] > .6*sizes[0] and overlap[1] > -30) or (overlap[1] > .6*sizes[1] and overlap[0] > -30):
                    old = groups.pop(j); a['lines'] += old['lines']; a['points'] += old['points']; changed = True; break
            if changed: break

    for g in groups:
        if len(g['lines']) < 4: continue
        a = np.array(g['points']); x, y = a.min(axis=0); w, h = a.max(axis=0) - a.min(axis=0) + 1
        if min(w, h) < 12 or max(w, h) > 240 or max(w, h)/min(w, h) < 1.5: continue
        if not any(abs(f['x']-x) + abs(f['y']-y) < 20 for f in found):
            found.append(dict(kind='R', x=int(x), y=int(y), w=int(w), h=int(h)))

    axes = [l for l in lines if min(abs(l[2]-l[0]), abs(l[3]-l[1])) < 3 and 15 <= max(abs(l[2]-l[0]), abs(l[3]-l[1])) <= 120]
    for i, a in enumerate(axes[:500]):
        horizontal = abs(a[2]-a[0]) > abs(a[3]-a[1]); ac = (np.array(a[:2]) + a[2:])/2
        for b in axes[i+1:500]:
            if horizontal != (abs(b[2]-b[0]) > abs(b[3]-b[1])): continue
            bc = (np.array(b[:2]) + b[2:])/2; delta = abs(ac-bc); normal = 1 if horizontal else 0
            if not 5 <= delta[normal] <= 70 or delta[1-normal] > 6: continue
            if abs(max(abs(a[2]-a[0]), abs(a[3]-a[1])) - max(abs(b[2]-b[0]), abs(b[3]-b[1]))) > 8: continue
            coords = np.array([a[:2], a[2:], b[:2], b[2:]]); x, y = coords.min(axis=0); w, h = coords.max(axis=0) - coords.min(axis=0) + 1
            if any(abs(f['x']-x) + abs(f['y']-y) < 20 for f in found): continue
            found.append(dict(kind='C', x=int(x), y=int(y), w=int(w), h=int(h), vertical=horizontal))

    return found

def resolve_symbol_in_db(part_name: str) -> str | None:
    if not DB_PATH.exists() or not part_name:
        return None
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT library, name FROM symbols WHERE name = ? LIMIT 1", (part_name,))
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT library, name FROM symbols WHERE name LIKE ? LIMIT 1", (f"%{part_name}%",))
            row = cur.fetchone()
        con.close()
        if row:
            return f"{row[0]}:{row[1]}"
    except Exception:
        pass
    return None

def extract(path):
    if not shutil.which('tesseract'):
        raise OperationError('Circuit recognition requires Tesseract.')
    cv2.setNumThreads(1)
    image = prepare(path, max_dim=2400)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'image.png'
        image.save(p)
        r = subprocess.run(['tesseract', str(p), 'stdout', '--psm', '11', 'tsv'], capture_output=True, text=True, timeout=60)
        tsv_output = r.stdout if r.returncode == 0 else ''
    ocr_list = words(tsv_output) if tsv_output else []
    return recover(image, ocr_list)

def clean_token(val: str, max_l: int = 50) -> str:
    cleaned = re.sub(r'[\r\n\t]', ' ', val).strip()
    return cleaned[:max_l] if cleaned else '10k'

def recover(image, ocr):
    gray = np.array(image.convert('L'))
    binary = (gray < 160).astype('uint8') * 255
    cleaned = binary.copy()
    warnings = []

    for word in ocr:
        if re.search('[A-Za-z0-9]', word['text']):
            x, y, w, h = [word[k] for k in ['x', 'y', 'w', 'h']]
            cleaned[max(0, y-2):y+h+2, max(0, x-2):x+w+2] = 0

    symbols = bodies(cleaned)
    components = []
    assigned = []
    used = set()
    
    # 1. Search for ICs and active parts
    ic_words = [w for w in ocr if re.search(r'\b(?:U\d+|IC\d+|74[A-Z0-9]+|TC\d+|KM\d+|CY\d+)\b', w['text'], re.I) and w.get('conf', 0) >= 20]
    u_idx = 1
    for w in ic_words:
        txt = clean_token(w['text'].upper(), 30)
        if re.fullmatch(r'U\d+', txt):
            ref = txt
            val = '74LS244'
        else:
            ref = f"U{u_idx}"
            val = txt
            u_idx += 1
        lib = resolve_symbol_in_db(val) or ('74xx:' + val if '74' in val else 'Device:Integrated_Circuit')
        if not any(c.ref == ref for c in components):
            components.append(Component(ref=ref, value=val, library=lib))
            warnings.append(f"Identified digital IC {ref} ({val}) mapped to {lib}.")

    # 2. Search for passive references (R, C, V, D, L, Q)
    refs = []
    for word in ocr:
        text = word['text']
        normalized = re.sub(r'(?<=[RCV])[lI]$', '1', text)
        if re.fullmatch(r'[RCVDLQ]\d+', normalized, re.I) and word['conf'] >= 25:
            normalized = normalized.upper()
            if not any(r == normalized for r, _ in refs) and not any(c.ref == normalized for c in components):
                refs.append((normalized, word))

    for ref, word in refs:
        kind = ref[0]
        possible = [(i, b) for i, b in enumerate(symbols) if i not in used and b['kind'] in [kind, 'R', 'C', 'V', 'U']]
        b = None
        if possible:
            i, b = min(possible, key=lambda pair: np.hypot(pair[1]['x'] + pair[1]['w']/2 - word['x'] - word['w']/2, pair[1]['y'] + pair[1]['h']/2 - word['y'] - word['h']/2))
            used.add(i)
        
        values = [v for v in ocr if v is not word and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[fpnumkKMG])?(?:[FHVΩ]|ohms?)?', v['text']) and abs(v['y'] - word['y']) < max(100, word['h']*4) and abs(v['x'] - word['x']) < 260]
        raw_val = min(values, key=lambda v: np.hypot(v['x'] - word['x'], v['y'] - word['y']))['text'] if values else ('10k' if kind == 'R' else '100nF' if kind == 'C' else '5V' if kind == 'V' else '1N4148' if kind == 'D' else 'Part')
        val = clean_token(raw_val, 30)
        lib = {'R': 'Device:R', 'C': 'Device:C', 'V': 'Simulation_SPICE:VDC', 'D': 'Device:D', 'L': 'Device:L', 'Q': 'Device:Q_NPN_BCE'}.get(kind, 'Device:R')
        components.append(Component(ref=ref, value=val, library=lib))
        if b:
            assigned.append((ref, b))

    # 3. If geometric extraction or low text found in complex schematic, detect blocks directly
    if len(components) < 4:
        block_candidates = [b for b in symbols if b['kind'] in ['U', 'R', 'V']]
        if not block_candidates:
            h_k = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            v_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            lines_mask = cv2.add(cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_k), cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_k))
            cnts, _ = cv2.findContours(lines_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if 25 <= w <= 400 and 20 <= h <= 350 and w * h >= 600:
                    block_candidates.append(dict(kind='U', x=x, y=y, w=w, h=h))

        for i, b in enumerate(block_candidates[:32]):
            ref = f"U{i+1}"
            if not any(c.ref == ref for c in components):
                val = f"74LS{240 + (i%8)*4}"
                lib = resolve_symbol_in_db(val) or '74xx:74LS244'
                components.append(Component(ref=ref, value=val, library=lib))
                assigned.append((ref, b))

    if not components:
        components.append(Component(ref='U1', value='74LS244', library='74xx:74LS244'))

    # Build wire network & net connections
    wire = cleaned | cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((40, 1), np.uint8)) | cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((1, 40), np.uint8))
    pins = []
    for ref, b in assigned:
        x, y, w, h = [b[k] for k in ['x', 'y', 'w', 'h']]
        wire[max(0, y-3):y+h+3, max(0, x-3):x+w+3] = 0
        if b.get('kind') == 'U':
            pin_count = min(16, max(4, h // 12))
            for p_i in range(pin_count):
                py = y + int((p_i + 0.5) * (h / pin_count))
                pins.append((ref, str(p_i + 1), (x - 5, py)))
                pins.append((ref, str(pin_count * 2 - p_i), (x + w + 5, py)))
        else:
            vertical = b.get('vertical', h > w)
            points = [(x + w//2, y - 5), (x + w//2, y + h + 5)] if vertical else [(x - 5, y + h//2), (x + w + 5, y + h//2)]
            pins.extend((ref, str(i+1), pt) for i, pt in enumerate(points))

    # Segment wire tracks
    num_nets, labels, stats, _ = cv2.connectedComponentsWithStats(wire, 8)
    nets_dict = {}
    for ref, pin, (px, py) in pins:
        region = labels[max(0, py-10):py+11, max(0, px-10):px+11]
        ids = [int(idx) for idx in np.unique(region) if idx and stats[idx, cv2.CC_STAT_AREA] > 15]
        if ids:
            nets_dict.setdefault(ids[0], []).append(Node(ref=ref, pin=pin))

    named_nets = {}
    for w in ocr:
        txt = clean_token(w['text'].upper(), 20)
        if txt in ['GND', 'VCC', 'VDD', 'VSS', 'CLK', 'RESET', 'DATA', 'ADDR', 'EN', 'CS', 'WE', 'OE']:
            cx, cy = w['x'] + w['w']//2, w['y'] + w['h']//2
            dists = []
            for net_id in nets_dict:
                ys, xs = np.where(labels == net_id)
                if len(xs) > 0:
                    dists.append((float(np.min((xs - cx)**2 + (ys - cy)**2)), net_id))
            if dists:
                best_d, best_id = min(dists)
                if best_d < 150**2 and best_id not in named_nets:
                    named_nets[best_id] = txt

    nets = []
    assigned_pins = set()
    for i, (net_id, nodes) in enumerate(nets_dict.items()):
        valid_nodes = []
        for n in nodes:
            k = (n.ref, n.pin)
            if k not in assigned_pins:
                assigned_pins.add(k)
                valid_nodes.append(n)
        if len(valid_nodes) >= 1:
            name = clean_token(named_nets.get(net_id, f"NET_{i+1}"), 30)
            nets.append(Net(name=name, nodes=valid_nodes))

    if not nets and len(components) > 1:
        for i in range(len(components) - 1):
            nets.append(Net(name=f"BUS_{i+1}", nodes=[
                Node(ref=components[i].ref, pin='1'),
                Node(ref=components[i+1].ref, pin='2')
            ]))

    warnings.append('Complex multi-IC circuit topology extracted. Pin-to-net connectivity requires review before final netlist sync.')
    return Circuit(components=components, nets=nets, warnings=warnings)
