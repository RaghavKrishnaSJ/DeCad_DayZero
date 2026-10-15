'use client';
import {useEffect,useState} from 'react';
import WorkbenchDialog from './WorkbenchDialog';
import {renameComponent,removeComponent,circuitErrors} from './review-model.mjs';
export default function CircuitReview({initial,source,request,onApply,onClose,busy,inspection=false}){
 const [circuit,setCircuit]=useState(()=>({...initial,nets:initial.nets||[]})),[error,setError]=useState(''),[reviewed,setReviewed]=useState(false),[preview,setPreview]=useState(null),[raw,setRaw]=useState(''),[advanced,setAdvanced]=useState(false);
 useEffect(()=>{
  if(!source)return;let active=true,url;
  request(source.path).then(r=>r.blob()).then(blob=>{
   const ext=source.name.split('.').at(-1).toLowerCase(),type={pdf:'application/pdf',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp'}[ext];
   if(!active||!type)return;url=URL.createObjectURL(new Blob([blob],{type}));setPreview({url,type});
  }).catch(e=>{if(active)setError('Source preview: '+e.message);});
  return ()=>{active=false;if(url)URL.revokeObjectURL(url);};
 },[source,request]);
 const update=next=>{setCircuit(next);setReviewed(false);setError('');};
 const component=(i,key,value)=>update({...circuit,components:circuit.components.map((c,j)=>j===i?{...c,[key]:value}:c)});
 const net=(i,value)=>update({...circuit,nets:circuit.nets.map((n,j)=>j===i?value:n)});
 const errors=circuitErrors(circuit);
 const apply=async()=>{try{setError('');await onApply(circuit);}catch(e){setError(e.message);}};
 return <WorkbenchDialog title={inspection?"Inspect current circuit":"Review circuit"} onClose={onClose} busy={busy}>
  <p>{inspection?"Inspect the saved component values and physical pin connections. Use schematic commands to edit the current design.":"Compare every reference, value and physical pin with the source. Check small passives, decoupling capacitors and faint symbols. Add missing components below; do not approve inferred connections."}</p>
  <div className={source?"review-comparison":"review-single"}>
  {source&&<aside className="review-source"><details open><summary>Source: {source.name}</summary>{preview?(preview.type==='application/pdf'?<iframe className="source-preview" title="Source schematic PDF" src={preview.url}/>:<img className="source-preview" alt="Original schematic for comparison" src={preview.url}/>):<p>Preview is loading, or this file type has no inline preview.</p>}</details></aside>}
  <div className="review-editor">
  {!!circuit.warnings?.length&&<div className="review-notices">{circuit.warnings.map((w,i)=><p key={i}>{w}</p>)}</div>}
  <div className="workflow-section-title"><h3>Components ({circuit.components.length})</h3><button disabled={busy||inspection} onClick={()=>update({...circuit,components:[...circuit.components,{ref:'',value:'',library:''}]})}>Add component</button></div>
  <div className="workflow-table"><table><thead><tr><th>Reference</th><th>Value</th><th>KiCad symbol</th><th/></tr></thead><tbody>{circuit.components.map((c,i)=><tr key={i}>
   <td><input disabled={busy||inspection} aria-label={`Component ${i+1} reference`} value={c.ref} onChange={e=>update(renameComponent(circuit,i,e.target.value.toUpperCase()))}/></td>
   <td><input disabled={busy||inspection} aria-label={`${c.ref} value`} value={c.value} onChange={e=>component(i,'value',e.target.value)}/></td>
   <td><input disabled={busy||inspection} aria-label={`${c.ref} KiCad symbol`} placeholder="Device:R" value={c.library||''} onChange={e=>component(i,'library',e.target.value||null)}/></td>
   <td><button disabled={busy||inspection} aria-label={`Remove ${c.ref||'component'}`} onClick={()=>update(removeComponent(circuit,i))}>Remove</button></td>
  </tr>)}</tbody></table></div>
  <div className="workflow-section-title"><h3>Connections ({circuit.nets.length} nets)</h3><button disabled={busy||inspection||!circuit.components.length} onClick={()=>update({...circuit,nets:[...circuit.nets,{name:'',nodes:[{ref:circuit.components[0].ref,pin:''}]}]})}>Add net</button></div>
  {!circuit.nets.length&&<p>No connections are defined. Add nets and their physical pins to create a connected circuit.</p>}
  {circuit.nets.map((n,i)=><fieldset className="review-net" key={i}><legend>Net {i+1}</legend><div className="workflow-row"><label>Net name<input disabled={busy||inspection} value={n.name} onChange={e=>net(i,{...n,name:e.target.value})}/></label><button disabled={busy||inspection} onClick={()=>update({...circuit,nets:circuit.nets.filter((_,j)=>j!==i)})}>Remove net</button></div>
   {n.nodes.map((p,j)=><div className="workflow-row" key={j}><label>Component<select disabled={busy||inspection} value={p.ref} onChange={e=>net(i,{...n,nodes:n.nodes.map((q,k)=>k===j?{...q,ref:e.target.value}:q)})}><option value="">Select component</option>{circuit.components.map((c,k)=><option key={k} value={c.ref}>{c.ref||'(unnamed)'}</option>)}</select></label><label>Physical pin<input disabled={busy||inspection} value={p.pin} onChange={e=>net(i,{...n,nodes:n.nodes.map((q,k)=>k===j?{...q,pin:e.target.value}:q)})}/></label><button disabled={busy||inspection} onClick={()=>net(i,{...n,nodes:n.nodes.filter((_,k)=>k!==j)})}>Remove pin</button></div>)}
   <button disabled={busy||inspection||!circuit.components.length} onClick={()=>net(i,{...n,nodes:[...n.nodes,{ref:circuit.components[0].ref,pin:''}]})}>Add pin</button>
  </fieldset>)}
  <button disabled={busy||inspection} onClick={()=>{setAdvanced(!advanced);setRaw(JSON.stringify(circuit,null,2));}}>Advanced JSON {advanced?'−':'+'}</button>
  {advanced&&<div><textarea className="review-json" aria-label="Circuit JSON" value={raw} onChange={e=>setRaw(e.target.value)}/><button disabled={busy||inspection} onClick={()=>{try{const value=JSON.parse(raw),problems=circuitErrors(value);if(problems.length)throw new Error(problems.join(' '));update(value);setAdvanced(false);}catch(e){setError(e.message);}}}>Use JSON changes</button></div>}
  {(error||errors.length>0)&&<div role="alert" className="workflow-error">{error||errors.join(' ')}</div>}
  {!inspection&&<label className="review-confirm"><input type="checkbox" disabled={busy||inspection} checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I checked the component values, symbols and pin connections against the source.</label>}
  </div></div>
  <div className="modal-actions"><button disabled={busy} onClick={onClose}>{inspection?'Close inspection':'Cancel'}</button>{!inspection&&<button className="btn-primary" disabled={busy||inspection||!reviewed||errors.length>0||advanced} onClick={apply}>{busy?'Applying…':'Apply reviewed circuit'}</button>}</div>
 </WorkbenchDialog>;
}
