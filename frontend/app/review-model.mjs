export function renameComponent(circuit, index, ref) {
  const old = circuit.components[index].ref;
  return {...circuit, components:circuit.components.map((c,i)=>i===index?{...c,ref}:c), nets:circuit.nets.map(n=>({...n,nodes:n.nodes.map(p=>p.ref===old?{...p,ref}:p)}))};
}
export function removeComponent(circuit,index) {
  const ref=circuit.components[index].ref;
  return {...circuit,components:circuit.components.filter((_,i)=>i!==index),nets:circuit.nets.map(n=>({...n,nodes:n.nodes.filter(p=>p.ref!==ref)})).filter(n=>n.nodes.length)};
}
export function circuitErrors(circuit) {
  const errors=[],refs=new Set(),names=new Set(),pins=new Set();
  if(!Array.isArray(circuit?.components)||!Array.isArray(circuit?.nets))return ['Components and nets must be lists.'];
  if(!circuit.components.length)errors.push('Add at least one component.');
  if(!circuit.nets.length)errors.push('No connections recovered. Define and review physical pin connections before applying.');
  if(circuit.warnings!==undefined&&(!Array.isArray(circuit.warnings)||circuit.warnings.some(w=>typeof w!=='string')))errors.push('Warnings must be a list of text.');
  for(const c of circuit.components){
    if(!/^[A-Z][A-Z0-9_]*\d+$/.test(c.ref))errors.push(`Invalid reference: ${c.ref || '(empty)'}.`);
    if(refs.has(c.ref))errors.push(`Duplicate reference: ${c.ref}.`);refs.add(c.ref);
    if(!String(c.value||'').trim()||['UNKNOWN','?','UNREADABLE'].includes(String(c.value).trim().toUpperCase()))errors.push(`${c.ref}: enter a value.`);
  }
  for(const n of circuit.nets){
    if(!n.name?.trim()||/[\r\n"\\]/.test(n.name))errors.push('Enter a valid net name.');
    if(names.has(n.name))errors.push(`Duplicate net: ${n.name}.`);names.add(n.name);
    if(!Array.isArray(n.nodes)||!n.nodes.length){errors.push(`${n.name}: add at least one pin.`);continue;}
    for(const p of n.nodes){
      if(!refs.has(p.ref))errors.push(`${n.name}: unknown component ${p.ref}.`);
      if(!String(p.pin||'').trim())errors.push(`${n.name}: enter a physical pin number.`);
      const key=JSON.stringify([p.ref,p.pin]);if(pins.has(key))errors.push(`${p.ref} pin ${p.pin} is assigned more than once.`);pins.add(key);
    }
  }
  return [...new Set(errors)];
}
export function boardErrors(plan,components){
 const errors=[];
 for(const k of ['width_mm','height_mm'])if(!Number.isFinite(+plan[k])||+plan[k]<10||+plan[k]>500)errors.push('Board dimensions must be 10–500 mm.');
 for(const k of ['track_width_mm','clearance_mm'])if(!Number.isFinite(+plan[k])||+plan[k]<.1||+plan[k]>2)errors.push('Track width and clearance must be 0.1–2 mm.');
 for(const c of components){const p=plan.placements[c.ref];
  if(!p?.footprint||!/^([^:\/\\]+):([^:\/\\]+)$/.test(p.footprint))errors.push(`${c.ref}: select an installed footprint.`);
  if(!p||![p.x_mm,p.y_mm,p.rotation_deg].every(x=>x!==''&&Number.isFinite(+x)))errors.push(`${c.ref}: enter numeric position and rotation.`);
  else if(+p.x_mm<2||+p.y_mm<2||+p.x_mm>+plan.width_mm-2||+p.y_mm>+plan.height_mm-2)errors.push(`${c.ref}: position must stay inside the 2 mm board margin.`);
 }
 return [...new Set(errors)];
}
