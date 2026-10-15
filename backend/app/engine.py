"""Native KiCad project operations. Connectivity always comes from KiCad XML."""
from __future__ import annotations
import copy
import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from collections import OrderedDict
import xml.etree.ElementTree as ET
from pathlib import Path
from .sexpr import Atom as A, child, children, dump, expr as E, num as N, parse

class OperationError(ValueError):
    pass

LOCKS = {}
LOCK_GUARD = threading.Lock()
CLI_LIMIT = threading.BoundedSemaphore(2)
CACHE_LOCK = threading.Lock()
EXPORT_CACHE = OrderedDict()

def project_lock(path):
    with LOCK_GUARD:
        return LOCKS.setdefault(str(path), threading.RLock())

def uid():
    return str(uuid.uuid4())

def atomic_text(path, text):
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as f:
        f.write(text)
        temp = Path(f.name)
    temp.replace(path)

def find_cli():
    return os.getenv('KICAD_CLI') or shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

def run_cli(*args):
    if not CLI_LIMIT.acquire(timeout=10):raise OperationError('KiCad is busy. Retry after the current checks finish.')
    try:
        result = subprocess.run([find_cli(), *map(str, args)], capture_output=True, text=True, timeout=90)
    except FileNotFoundError as e:
        raise OperationError('KiCad CLI is unavailable. Start the Docker package or configure KICAD_CLI.') from e
    except subprocess.TimeoutExpired as e:
        raise OperationError('KiCad operation timed out.') from e
    finally:CLI_LIMIT.release()
    if result.returncode:
        raise OperationError((result.stderr or result.stdout or 'KiCad operation failed').strip()[-3000:])
    return result

LIBRARY_CACHE = {}

def library_dir():
    candidates = [
        os.getenv('KICAD_SYMBOL_DIR',''),
        str(Path(__file__).resolve().parents[2] / 'libraries' / 'kicad' / 'official' / 'symbols'),
        '/usr/share/kicad/symbols',
        '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
    ]
    return next((Path(p) for p in candidates if p and Path(p).is_dir()), None)

def find_symbol_library_path(name):
    if not name or any(x in name for x in ['/', '\\', '..']):
        raise OperationError('Invalid symbol library identifier.')
    search_dirs = [
        library_dir(),
        Path(__file__).resolve().parents[2] / 'libraries' / 'kicad' / 'community' / 'digikey',
        Path(__file__).resolve().parents[2] / 'libraries' / 'kicad' / 'community' / 'sparkfun',
        Path(__file__).resolve().parents[2] / 'libraries' / 'kicad' / 'community' / 'seeed'
    ]
    for folder in search_dirs:
        if folder and folder.is_dir():
            target_sym = folder / f'{name}.kicad_sym'
            if target_sym.is_file():
                return target_sym
            target_dir = folder / f'{name}.kicad_symdir'
            if target_dir.is_dir():
                return target_dir
            for nested in folder.rglob(f'{name}.kicad_sym'):
                if nested.is_file():
                    return nested
            for nested_dir in folder.rglob(f'{name}.kicad_symdir'):
                if nested_dir.is_dir():
                    return nested_dir
    return None

def load_library(name):
    target = find_symbol_library_path(name)
    if not target:
        raise OperationError(f'KiCad symbol library {name} is unavailable.')
    if name not in LIBRARY_CACHE:
        catalog = {}
        if target.is_dir():
            for f in target.glob('*.kicad_sym'):
                try:
                    tree = parse(f.read_text())
                    for s in children(tree, 'symbol'):
                        if len(s) > 1 and isinstance(s[1], str):
                            catalog[s[1]] = s
                except Exception:
                    pass
        else:
            tree = parse(target.read_text())
            catalog = {s[1]: s for s in children(tree, 'symbol')}
        LIBRARY_CACHE[name] = catalog
    return LIBRARY_CACHE[name]

def library_symbol(lib_id):
    if ':' not in lib_id:
        raise OperationError('Symbol must be specified as Library:Name.')
    lib, name = lib_id.split(':',1)
    catalog = load_library(lib)
    def resolve(symbol_name, visited):
        if symbol_name in visited or symbol_name not in catalog:
            raise OperationError(f'Unknown or cyclic symbol {lib}:{symbol_name}')
        s = copy.deepcopy(catalog[symbol_name])
        ext = child(s,'extends')
        if ext:
            base = resolve(ext[1], visited | {symbol_name})
            overrides = {p[1]:p for p in children(s,'property')}
            result = [A('symbol'),symbol_name]
            for item in base[2:]:
                if isinstance(item,list) and item[0]=='property':
                    result.append(overrides.pop(item[1],item))
                elif isinstance(item,list) and item[0]=='symbol':
                    item[1] = symbol_name + item[1][len(base[1]):]
                    result.append(item)
                else:
                    result.append(item)
            result.extend(overrides.values())
            s = result
        return s
    s = resolve(name,set())
    s[1] = lib_id
    return s

DEFAULT_SYMBOLS = {'R':'Device:R','C':'Device:C','L':'Device:L','D':'Device:D','Q':'Transistor_BJT:Q_NPN_BCE','V':'Simulation_SPICE:VDC','I':'Simulation_SPICE:IDC','J':'Connector_Generic:Conn_01x02'}

def effects():
    return E('effects',E('font',E('size',N(1.27),N(1.27))))

class Schematic:
    def __init__(self, project):
        self.project = Path(project)
        self.path = next(self.project.glob('*.kicad_sch'),None)
        if not self.path:
            raise OperationError('Project has no KiCad schematic.')
        try:
            self.tree = parse(self.path.read_text())
        except (ValueError, OSError) as e:
            raise OperationError(f'Invalid schematic source: {e}') from e
        if not self.tree or self.tree[0] != 'kicad_sch':
            raise OperationError('Invalid KiCad schematic.')
        if not child(self.tree,'uuid'):
            self.tree.insert(3,E('uuid',uid()))

    @staticmethod
    def create(project, name):
        project.mkdir(parents=True)
        tree = E('kicad_sch', E('version',A('20231120')),E('generator',A('eeschema')),E('uuid',uid()), E('paper','A4'), E('lib_symbols'))
        atomic_text(project/f'{name}.kicad_sch',dump(tree)+'\n')
        atomic_text(project/f'{name}.kicad_pro',json.dumps({'meta':{'version':1}}))

    def save(self):
        atomic_text(self.path,dump(self.tree)+'\n')

    def symbols(self):
        return [s for s in children(self.tree,'symbol') if child(s,'lib_id')]

    def reference(self,s):
        return next((p[2] for p in children(s,'property') if p[1]=='Reference'),'')

    def get(self,ref):
        return next((s for s in self.symbols() if self.reference(s)==ref),None)

    def property(self,s,name):
        return next((p[2] for p in children(s,'property') if p[1]==name),'')

    def add(self, ref, value, lib_id=None, footprint=None, x=None,y=None,angle=0):
        if self.get(ref):
            raise OperationError(f'{ref} already exists. Use change/set to update it.')
        if not lib_id:
            if ref.startswith('U'):
                matches = []
                for library in ['74xx','Amplifier_Operational','Timer','MCU_ST_STM32F4','Memory_RAM']:
                    try:
                        if value in load_library(library): matches.append(f'{library}:{value}')
                    except OperationError: pass
                if not matches:
                    db_path = Path(__file__).resolve().parents[2] / 'libraries' / 'index' / 'components.db'
                    if db_path.exists():
                        try:
                            import sqlite3
                            with sqlite3.connect(str(db_path)) as conn:
                                cur = conn.cursor()
                                cur.execute("SELECT lib_id FROM symbols WHERE name = ? COLLATE NOCASE LIMIT 5", (value,))
                                rows = cur.fetchall()
                                matches.extend(r[0] for r in rows)
                        except Exception: pass
                if len(matches)!=1:
                    raise OperationError(f'Choose the exact KiCad Library:Symbol for {ref} ({value}); found: {matches if matches else "none"}.')
                lib_id=matches[0]
            else:
                lib_id=DEFAULT_SYMBOLS.get(ref[0])
                if not lib_id: raise OperationError(f'Specify Library:Symbol for {ref}.')
        definition=library_symbol(lib_id)
        lib=child(self.tree,'lib_symbols')
        if lib is None:
            lib=E('lib_symbols');self.tree.append(lib)
        if not any(s[1]==lib_id for s in children(lib,'symbol')):lib.append(definition)
        idx=len(self.symbols())
        if x is None:
            col = idx % 6
            x = 38.0 + col * 36.0
        else:
            x = float(x)
        if y is None:
            row = (idx // 6) % 5
            y = 35.0 + row * 28.0
        else:
            y = float(y)
        symbol_id=uid()
        s=E('symbol',E('lib_id',lib_id),E('at',N(x),N(y),N(angle)),E('unit',A('1')),E('in_bom',A('yes')),E('on_board',A('yes')),E('dnp',A('no')),E('uuid',symbol_id))
        # Keep fields above both symbol body and outward net-label stubs.
        pin_offsets=[float(child(pin,'at')[2]) for pin in self.definition_pins(definition,1)]
        field_y=y-max([0,*pin_offsets])-12.7
        props={'Reference':ref,'Value':value,'Footprint':footprint or next((p[2] for p in children(definition,'property') if p[1]=='Footprint'),''),'Datasheet':next((p[2] for p in children(definition,'property') if p[1]=='Datasheet'),'')}
        for i,(key,val) in enumerate(props.items()):
            e=effects()
            if i>1:e.append(E('hide',A('yes')))
            s.append(E('property',key,val,E('at',N(x),N(field_y+i*2.54),N(angle)),e))
        for pin in self.definition_pins(definition,1):
            s.append(E('pin',child(pin,'number')[1],E('uuid',uid())))
        root_id=child(self.tree,'uuid')[1]
        s.append(E('instances',E('project',self.project.name,E('path','/'+root_id,E('reference',ref),E('unit',A('1'))))))
        self.tree.append(s)
        # Multi-unit packages share one reference, including their power unit.
        units=sorted({int(block[1].rsplit('_',2)[1]) for block in children(definition,'symbol') if len(block[1].rsplit('_',2))==3 and block[1].rsplit('_',2)[1].isdigit() and int(block[1].rsplit('_',2)[1])>1 and block[1].rsplit('_',2)[2] in ('0','1')})
        for index,unit in enumerate(units,1):
            extra=copy.deepcopy(s);child(extra,'uuid')[1]=uid();child(extra,'unit')[1]=A(str(unit))
            child(extra,'at')[2]=N(y+index*30.48)
            for prop in children(extra,'property'):child(prop,'at')[2]=N(float(child(prop,'at')[2])+index*30.48)
            extra[:]=[n for n in extra if not(isinstance(n,list) and n and n[0]=='pin')]
            for pin in self.definition_pins(definition,unit):extra.append(E('pin',child(pin,'number')[1],E('uuid',uid())))
            path=child(child(child(extra,'instances'),'project'),'path');child(path,'unit')[1]=A(str(unit))
            self.tree.append(extra)
        return {'ref':ref,'value':value,'library':lib_id,'action':'added'}

    def set_value(self,ref,value):
        symbols=[s for s in self.symbols() if self.reference(s)==ref]
        if not symbols:raise OperationError(f'{ref} does not exist.')
        for symbol in symbols:
            next(p for p in children(symbol,'property') if p[1]=='Value')[2]=value
        return {'ref':ref,'value':value,'action':'modified'}

    def remove(self,ref):
        symbols=[s for s in self.symbols() if self.reference(s)==ref]
        if not symbols:raise OperationError(f'{ref} does not exist.')
        positions={tuple(round(v,4) for v in point) for symbol in symbols for point in self.pin_positions(symbol).values()}
        ends=set(positions);remove=[]
        for wire in children(self.tree,'wire'):
            points=[tuple(round(float(v),4) for v in p[1:3]) for p in children(child(wire,'pts'),'xy')]
            if any(p in positions for p in points):remove.append(wire);ends.update(points)
        self.tree[:]=[n for n in self.tree if all(n is not x for x in [*symbols,*remove]) and not(isinstance(n,list) and n and n[0]=='label' and tuple(round(float(v),4) for v in child(n,'at')[1:3]) in ends)]
        return {'ref':ref,'action':'removed'}

    def definition_pins(self,definition,unit):
        pins=[]
        for block in children(definition,'symbol'):
            suffix=block[1].rsplit('_',2)
            if len(suffix)==3 and suffix[1] in ('0',str(unit)) and suffix[2] in ('0','1'):
                pins.extend(children(block,'pin'))
        return pins

    def pin_positions(self,s):
        lib=child(self.tree,'lib_symbols');lib_id=child(s,'lib_id')[1]
        definition=next((d for d in children(lib,'symbol') if d[1]==lib_id),None)
        if definition is None:raise OperationError(f'Embedded symbol {lib_id} missing.')
        at=child(s,'at');cx,cy,angle=map(float,at[1:4]); theta=math.radians(angle)
        mirror=child(s,'mirror');result={}
        for p in self.definition_pins(definition,int(child(s,'unit',[None,1])[1])):
            a=child(p,'at');dx,dy=map(float,a[1:3])
            if mirror and mirror[1]=='x':dy=-dy
            if mirror and mirror[1]=='y':dx=-dx
            x=cx+dx*math.cos(theta)-dy*math.sin(theta)
            y=cy-(dx*math.sin(theta)+dy*math.cos(theta))
            result[str(child(p,'number')[1])]=(x,y)
        return result

    def connect(self,net,nodes):
        if not nodes:raise OperationError('Specify at least one component pin, for example connect net GND to R1 pin 2.')
        edits=[]
        pin_coords = []
        for ref,pin in nodes:
            symbols=[symbol for symbol in self.symbols() if self.reference(symbol)==ref]
            if not symbols:raise OperationError(f'Unknown component {ref}.')
            s=next((symbol for symbol in symbols if str(pin) in self.pin_positions(symbol)),symbols[0])
            pos=self.pin_positions(s).get(str(pin))
            if not pos:raise OperationError(f'{ref} has no pin {pin}.')
            x,y=pos
            # Named net stubs preserve connectivity without routing a guessed
            # Manhattan path through unrelated symbol pins or other nets.
            center=child(s,'at');dx=x-float(center[1]);dy=y-float(center[2])
            horizontal=abs(dx)>abs(dy)
            ex=x+(5.08 if dx>=0 else -5.08) if horizontal else x
            ey=y if horizontal else y+(5.08 if dy>=0 else -5.08)
            existing=next((l for l in children(self.tree,'label') if abs(float(child(l,'at')[1])-ex)<1e-4 and abs(float(child(l,'at')[2])-ey)<1e-4),None)
            if existing:existing[1]=net
            else:
                self.tree.append(E('wire',E('pts',E('xy',N(x),N(y)),E('xy',N(ex),N(ey))),E('stroke',E('width',N(0)),E('type',A('default'))),E('uuid',uid())))
                angle=0
                label_effects=effects()
                if horizontal and dx<0:
                    justify=child(label_effects,'justify')
                    if justify:justify[1:]=[A('right'),A('bottom')]
                    else:label_effects.append(E('justify',A('right'),A('bottom')))
                self.tree.append(E('label',net,E('at',N(ex),N(ey),N(angle)),label_effects,E('uuid',uid())))
            edits.append({'ref':ref,'pin':str(pin),'net':net,'action':'connected'})
        return edits

    def cached_export(self,operation,compute):
        # Include child sheets so a hierarchy edit invalidates every derived output.
        fingerprint=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted([*self.project.rglob('*.kicad_sch'),*self.project.rglob('*.kicad_pro')]) if '.history' not in p.parts and '.redo' not in p.parts)
        key=(str(self.project.resolve()),operation,fingerprint)
        with CACHE_LOCK:
            if key in EXPORT_CACHE:
                EXPORT_CACHE.move_to_end(key)
                return copy.deepcopy(EXPORT_CACHE[key])
        result=compute()
        with CACHE_LOCK:
            EXPORT_CACHE[key]=copy.deepcopy(result)
            while len(EXPORT_CACHE)>32:EXPORT_CACHE.popitem(last=False)
        return result

    def netlist(self):return self.cached_export('netlist',self._netlist)

    def _netlist(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'net.xml';run_cli('sch','export','netlist','--format','kicadxml','-o',out,self.path)
            if not out.exists():raise OperationError('KiCad did not produce a netlist.')
            return out.read_text()

    def graph(self):
        root=ET.fromstring(self.netlist());components=[];nets=[]
        for c in root.findall('./components/comp'):
            part=c.find('libsource');fields={f.attrib['name']:f.text or '' for f in c.findall('./fields/field')}
            components.append({'ref':c.attrib['ref'],'value':c.findtext('value',''),'footprint':c.findtext('footprint',''),'library':f"{part.attrib.get('lib','')}:{part.attrib.get('part','')}" if part is not None else '', 'fields':fields})
        for net in root.findall('./nets/net'):
            nets.append({'name':net.attrib['name'].lstrip('/') if net.attrib['name'].count('/')==1 else net.attrib['name'],'class':net.attrib.get('class','Default'),'nodes':[{'ref':n.attrib['ref'],'pin':n.attrib['pin']} for n in net.findall('node')]})
        return {'components':components,'nets':nets}

    def erc(self):return self.cached_export('erc',self._erc)

    def _erc(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'erc.json';run_cli('sch','erc','--format','json','-o',out,self.path)
            if not out.exists():raise OperationError('KiCad did not produce an ERC report.')
            report=json.loads(out.read_text())
            violations=[v for s in report.get('sheets',[]) for v in s.get('violations',[])]
            violations.extend(report.get('violations',[]))
            return {'status':'completed','passed':not any(v.get('severity')=='error' for v in violations),'violations':violations,'report':report}

    def preview(self):return self.cached_export('preview',self._preview)

    def highlight_preview(self,svg,ref):
        points=[point for symbol in self.symbols() if self.reference(symbol)==ref for point in self.pin_positions(symbol).values()]
        if not points:return svg
        x=min(p[0] for p in points)-4;y=min(p[1] for p in points)-4
        w=max(10,max(p[0] for p in points)-x+4);h=max(10,max(p[1] for p in points)-y+4)
        overlay=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#639fff" fill-opacity="0.12" stroke="#3276cc" stroke-width="0.5" stroke-dasharray="1 0.6"/>'
        return svg.replace('</svg>',overlay+'</svg>')

    def content_preview(self):
        import re
        svg=self.cached_export('content-svg',lambda:self._preview(True))
        points=[]
        for symbol in self.symbols():
            points.extend(self.pin_positions(symbol).values())
            for prop in children(symbol,'property'):
                if prop[1] not in ('Reference','Value'):continue
                at=child(prop,'at');x,y=float(at[1]),float(at[2]);width=max(6,len(str(prop[2]))*1.1)
                points.extend([(x-width/2,y-2),(x+width/2,y+2)])
        for wire in children(self.tree,'wire'):
            points.extend(tuple(map(float,p[1:3])) for p in children(child(wire,'pts'),'xy'))
        for label in children(self.tree,'label'):
            at=child(label,'at');x,y=float(at[1]),float(at[2]);width=max(5,len(label[1])*1.1)
            points.extend([(x-width,y-2),(x+width,y+2)])
        if not points:return svg
        left=min(x for x,y in points)-10;top=min(y for x,y in points)-10
        width=max(40,max(x for x,y in points)-left+10);height=max(35,max(y for x,y in points)-top+10)
        svg=re.sub(r'viewBox="[^"]+"',f'viewBox="{left} {top} {width} {height}"',svg,count=1)
        svg=re.sub(r'width="[^"]+" height="[^"]+"',f'width="{width}mm" height="{height}mm"',svg,count=1)
        return svg

    def _preview(self,content=False):
        with tempfile.TemporaryDirectory() as td:
            run_cli('sch','export','svg',*(['--exclude-drawing-sheet','--no-background-color'] if content else []),'-o',td+'/',self.path)
            pages=sorted(Path(td).glob('*.svg'))
            if not pages:raise OperationError('KiCad did not produce an SVG preview.')
            return pages[0].read_text()
