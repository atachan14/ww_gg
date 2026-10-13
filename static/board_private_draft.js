/* Viewer-owned truthful evidence, never a public CO/report draft. */
(() => {
 const copy=value=>JSON.parse(JSON.stringify(value));
 window.createBoardPrivateDraftStore=({boardId,revision,storage=null,scopeRevision=true})=>{
  if(typeof boardId!=='string'||!Number.isInteger(revision))throw Error('Board identity required');
  const drafts=new Map();
  const key=(player,role,team=[])=>`${boardId}:${scopeRevision?revision:'board'}:${player}:${role}${team.length?':'+[...team].sort((a,b)=>a-b).join('-'):''}`;
  const validate=(results)=>{
   if(!Array.isArray(results))throw Error('Private result list required');
   const days=new Set();
   return results.map(result=>{
    if(!Number.isInteger(result.day)||result.day<1||days.has(result.day))throw Error('Invalid private result day');
    days.add(result.day);
    if(result.target!==null&&(!Number.isInteger(result.target)||result.target<1))throw Error('Invalid private target');
    if(![null,'white','black'].includes(result.color))throw Error('Invalid private color');
    return {day:result.day,target:result.target,color:result.color};
   }).sort((a,b)=>a.day-b.day);
  };
  const save=(id,value)=>{drafts.set(id,copy(value));try{storage?.setItem(`wwgg-private:${id}`,JSON.stringify(value));}catch(_){}return copy(value);};
  return {
   open:({player,role,team=[],claims=[],publicResults=[]})=>{
    if(!Number.isInteger(player)||player<1||!['seer','medium','hunter','wolf'].includes(role))throw Error('Invalid private viewer');
    const id=key(player,role,team);
    if(drafts.has(id))return copy(drafts.get(id));
    try{
     const saved=JSON.parse(storage?.getItem(`wwgg-private:${id}`)||'null');
     if(saved?.boardId===boardId&&(!scopeRevision||saved.revision===revision)&&saved.player===player&&saved.role===role){saved.results=validate(saved.results);return save(id,{...saved,revision});}
    }catch(_){}
    // Copy only when constructing this private row for the first time. An
    // intentionally cleared row remains empty on reopen; do not refill it.
    const results=claims.includes(role)?publicResults.filter(r=>(r.player??r.reporter)===player&&(r.role??role)===role).map(r=>({day:r.day,target:r.target??null,color:r.color??null})):[];
    return save(id,{boardId,revision,player,role,team,results:validate(results)});
   },
   edit:({player,role,team=[],results})=>{
    const id=key(player,role,team),current=drafts.get(id);
    if(!current)throw Error('Open private row before editing');
    return save(id,{...current,results:validate(results)});
   },
   // Only a private-view calculation adapter consumes this payload. It has no
   // CO event, public-log batch or publication operation.
   snapshot:({player,role,team=[]})=>{const value=drafts.get(key(player,role,team));return value?copy(value):null;}
  };
 };
})();
