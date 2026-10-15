"""CPU symbol geometry + OCR association + raster wire topology for schematics.
Supports clean labeled R/C/V diagrams. Complex devices require detailed vision.
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
    if max(image.size)<800:
        factor=800/max(image.size)
        image=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.LANCZOS)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'image.png'
        image.save(p)
        r = subprocess.run(['tesseract', str(p), 'stdout', '--psm', '11', 'tsv'], capture_output=True, text=True, timeout=60)
        tsv_output = r.stdout if r.returncode == 0 else ''
        ocr_list=words(tsv_output) if tsv_output else []
        if max(image.size)<=1400:
            enlarged=Path(td)/'detail.png';image.resize((image.width*2,image.height*2),Image.Resampling.LANCZOS).save(enlarged)
            detail=subprocess.run(['tesseract',str(enlarged),'stdout','--psm','11','tsv'],capture_output=True,text=True,timeout=60)
            if detail.returncode==0:
                for word in words(detail.stdout):
                    ocr_list.append({**word,**{key:round(word[key]/2) for key in ('x','y','w','h')}})
    return recover(image, ocr_list)

def clean_token(val: str, max_l: int = 50) -> str:
    cleaned = re.sub(r'[\r\n\t]', ' ', val).strip()
    return cleaned[:max_l] if cleaned else 'UNKNOWN'

def recover(image, ocr):
    """Recover clean R/C/V diagrams; never invent unidentified devices or wires."""
    gray=np.array(image.convert('L'));binary=(gray<200).astype('uint8')*255;cleaned=binary.copy()
    refs=[];net_words=[]
    for word in ocr:
        raw=word['text'];normalized=re.sub(r'(?<=[RCV])[lI]$', '1',raw.upper())
        if re.fullmatch(r'[RCV]\d+',normalized) and word['conf']>=25:
            refs.append((normalized,word));mask=True
        elif re.fullmatch(r'[UJQDL]\d+',normalized) or re.fullmatch(r'(?:74[A-Z0-9]+|LM\d+[A-Z]*|NE\d+[A-Z]*)',normalized):
            raise OperationError('Geometric recognition cannot verify active-device pinouts. Select detailed vision or import a native netlist.')
        elif re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[fpnumkKMG])?(?:[FHVΩ]|ohms?)?',raw) and word['h']>=5 and word['w']/word['h']<10:mask=True
        else:
            # Tesseract can include a junction/leader before a net label.
            first=re.search(r'[A-Za-z]',raw);token=raw[first.start():].upper() if first else ''
            mask=token in ('VIN','VOUT','GND','VCC','VDD','VSS','OUT','IN')
            if mask:
                shift=round(word['w']*first.start()/len(raw))
                word={**word,'x':word['x']+shift,'w':word['w']-shift,'text':token};net_words.append(word)
        if mask:
            x,y,w,h=[word[k] for k in ('x','y','w','h')]
            cleaned[max(0,y-2):y+h+2,max(0,x-2):x+w+2]=0
    symbols=bodies(cleaned);components=[];assigned=[];used=set()
    for ref,word in refs:
        if ref in {c.ref for c in components}:continue
        kind=ref[0];candidates=[(i,b) for i,b in enumerate(symbols) if i not in used and b['kind']==kind]
        if not candidates:raise OperationError(f'{ref}: could not associate a symbol with its reference/value. Use detailed vision or a clearer scan.')
        i,body=min(candidates,key=lambda pair:np.hypot(pair[1]['x']+pair[1]['w']/2-word['x'],pair[1]['y']+pair[1]['h']/2-word['y']))
        distance=np.hypot(body['x']+body['w']/2-word['x'],body['y']+body['h']/2-word['y'])
        if distance>max(260,image.width*.24):raise OperationError(f'{ref}: ambiguous reference/value association.')
        used.add(i)
        candidates=[v for v in ocr if v['h']>=5 and v['w']/v['h']<10 and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[fpnumkKMG])?(?:[FHVΩ]|ohms?)?',v['text']) and abs(v['x']-word['x'])<max(50,word['w']*3) and 0<v['y']-word['y']<max(90,word['h']*5)]
        if not candidates:
            # Re-read the actual value pixels with a numeric alphabet. This
            # handles OCR glyph confusions such as 5/S without guessing values.
            from PIL import ImageOps
            nearby=[v for v in ocr if v['h']>=5 and abs(v['x']-word['x'])<max(50,word['w']*3) and 0<v['y']-word['y']<max(90,word['h']*5)]
            for v in nearby:
                crop=image.crop((max(0,v['x']-2),max(0,v['y']-2),v['x']+v['w']+2,v['y']+v['h']+2))
                crop=ImageOps.expand(crop.resize((crop.width*3,crop.height*3)),border=15,fill='white')
                with tempfile.TemporaryDirectory() as td:
                    target=Path(td)/'value.png';crop.save(target)
                    result=subprocess.run(['tesseract',str(target),'stdout','--psm','7','-c','tessedit_char_whitelist=0123456789.fpnumkKMGFHV+-'],capture_output=True,text=True,timeout=15)
                token=result.stdout.strip()
                if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[fpnumkKMG])?(?:[FHV])?',token):candidates.append({**v,'text':token})
        if not candidates:raise OperationError(f'{ref}: unreadable reference/value. Correct the source or use detailed vision; a default value will not be substituted.')
        value=min(candidates,key=lambda v:np.hypot(v['x']-word['x'],v['y']-word['y']))['text']
        components.append(Component(ref=ref,value=value,library={'R':'Device:R','C':'Device:C','V':'Simulation_SPICE:VDC'}[kind]));assigned.append((ref,body))
    if not components:raise OperationError('No reliable reference/value pairs were recovered. Use detailed vision or supply a circuit netlist.')
    # Reject clearly visible unassigned passive symbols, rather than omit them.
    for i,b in enumerate(symbols):
        if i in used:continue
        if b['kind']=='U':raise OperationError('Unidentified active-device body. Use detailed vision to verify the complete component inventory and pinout.')
        if b['kind'] not in ('R','C','V'):continue
        if not b.get('closed') and not(b['kind']=='C' and b['w']>35 and b['h']>20):continue
        if any(a['x']-12<=b['x']+b['w']/2<=a['x']+a['w']+12 and a['y']-12<=b['y']+b['h']/2<=a['y']+a['h']+12 for _,a in assigned):continue
        raise OperationError('A visible component has no readable reference/value. Review the source with detailed vision.')
    wire=cleaned.copy();pins=[]
    for ref,b in assigned:
        x,y,w,h=[b[k] for k in ('x','y','w','h')]
        wire[max(0,y-3):y+h+3,max(0,x-3):x+w+3]=0
        vertical=b.get('vertical',h>w)
        # Voltage source circles have equal dimensions; default upright polarity.
        if ref.startswith('V'):vertical=True
        pts=[(x+w//2,y-6),(x+w//2,y+h+6)] if vertical else [(x-6,y+h//2),(x+w+6,y+h//2)]
        pins.extend((ref,str(i+1),pt) for i,pt in enumerate(pts))
    # Four-way crossings without a dot cannot be assigned electrical semantics.
    horizontal=cv2.morphologyEx(wire,cv2.MORPH_OPEN,np.ones((1,19),np.uint8))
    vertical=cv2.morphologyEx(wire,cv2.MORPH_OPEN,np.ones((19,1),np.uint8))
    count,cross_labels,stats,centers=cv2.connectedComponentsWithStats(horizontal&vertical,8)
    for cx,cy in centers[1:]:
        x,y=int(round(cx)),int(round(cy));radius=9
        if x<radius or y<radius or x+radius>=image.width or y+radius>=image.height:continue
        if all((horizontal[y-1:y+2,x-radius:x-radius+2].any(),horizontal[y-1:y+2,x+radius-1:x+radius+1].any(),vertical[y-radius:y-radius+2,x-1:x+2].any(),vertical[y+radius-1:y+radius+1,x-1:x+2].any())):
            if np.count_nonzero(wire[y-4:y+5,x-4:x+5])<50:raise OperationError('Unmarked wire crossing is ambiguous. Add a junction dot or use detailed vision.')
    _,labels,stats,_=cv2.connectedComponentsWithStats(wire,8);groups={}
    for ref,pin,(px,py) in pins:
        options=[]
        for y in range(max(0,py-10),min(image.height,py+11)):
            for x in range(max(0,px-10),min(image.width,px+11)):
                label=int(labels[y,x])
                if label and stats[label,cv2.CC_STAT_AREA]>15:options.append(((x-px)**2+(y-py)**2,label))
        if not options:raise OperationError(f'{ref} pin {pin}: unresolved connection. Review the source before generating a circuit.')
        label=min(options)[1];groups.setdefault(label,[]).append(Node(ref=ref,pin=pin))
    names={}
    for word in net_words:
        cx,cy=word['x']+word['w']/2,word['y']+word['h']/2;distances=[]
        for label in groups:
            ys,xs=np.where(labels==label)
            distances.append((float(np.min((xs-cx)**2+(ys-cy)**2)),label))
        if distances:
            distance,label=min(distances)
            if distance<150**2:names[label]=word['text']
    merged={}
    for i,(label,nodes) in enumerate(groups.items(),1):merged.setdefault(names.get(label,f'NET_{i}'),[]).extend(nodes)
    nets=[Net(name=name,nodes=nodes) for name,nodes in merged.items()]
    return Circuit(components=components,nets=nets,warnings=['Geometric recovery supports clean, labeled R/C/V diagrams only. Verify all values, source polarity and wire junctions against the original.'])
