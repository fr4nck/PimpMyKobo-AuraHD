/* PMKB Notes V0.2 — portable host-only data model.
 * No filesystem, network, hardware access, timers or DOM dependencies.
 */
(function(root) {
  "use strict";
  const FORMAT="pmkb-notes-v1";
  const MAX_NOTES=100;
  const MAX_TITLE=100;
  const MAX_TEXT=120000;
  const MAX_STROKES=250;
  const MAX_POINTS=1200;
  const MAX_IMPORT_BYTES=3000000;
  const PAGE=Object.freeze({width:900,height:600});
  const BRUSHES=Object.freeze([2,5,11]);
  const FONTS=Object.freeze(["mono","sans","serif","handwriting"]);
  const DEFAULT_TYPE=Object.freeze({font:"mono",size:17,lineHeight:1.6});
  function typography(value) {
    if(value===undefined) return {...DEFAULT_TYPE}; // V0.1 JSON compatibility
    if(!plain(value) || typeof value.font!=="string" ||
      !(FONTS.includes(value.font)||/^import:[a-f0-9]{12}$/.test(value.font)) ||
      !Number.isInteger(value.size) || value.size<12 || value.size>36 ||
      ![1.2,1.4,1.6,1.8,2].includes(value.lineHeight)) {
      fail("Typographie invalide");
    }
    return {font:value.font,size:value.size,lineHeight:value.lineHeight};
  }

  function fail(message) {throw new Error(message);}
  function plain(value) {return value!==null && typeof value==="object" && !Array.isArray(value);}
  function date(value) {
    return typeof value==="string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(value)
      && !Number.isNaN(Date.parse(value));
  }
  function goodId(value) {return typeof value==="string" && /^[a-z0-9_-]{6,72}$/.test(value);}
  function point(x,y) {
    const a=Math.round(Number(x)),b=Math.round(Number(y));
    if(!Number.isFinite(a)||!Number.isFinite(b)) fail("Coordonnées invalides");
    return [Math.min(PAGE.width,Math.max(0,a)),Math.min(PAGE.height,Math.max(0,b))];
  }
  function stroke(tool,width,points) {
    if(!["pen","eraser"].includes(tool) || !BRUSHES.includes(width) ||
        !Array.isArray(points) || points.length<1 || points.length>MAX_POINTS) {
      fail("Trait invalide");
    }
    return {tool,width,points:points.map(p=>{
      if(!Array.isArray(p)||p.length!==2||
          !Number.isInteger(p[0])||!Number.isInteger(p[1])||
          p[0]<0||p[0]>PAGE.width||p[1]<0||p[1]>PAGE.height) {
        fail("Point invalide");
      }
      return [p[0],p[1]];
    })};
  }
  function blank(id,now) {
    if(!goodId(id)||!date(now)) fail("Identifiant ou date invalide");
    return {id,title:"Sans titre",text:"",strokes:[],typography:typography(),created:now,updated:now};
  }
  function note(value) {
    if(!plain(value) || !goodId(value.id) || typeof value.title!=="string" ||
      !value.title.trim() || value.title.length>MAX_TITLE ||
      typeof value.text!=="string" || value.text.length>MAX_TEXT ||
      !date(value.created)||!date(value.updated) ||
      !Array.isArray(value.strokes)||value.strokes.length>MAX_STROKES) {
      fail("Note invalide");
    }
    return {
      id:value.id,title:value.title,text:value.text,typography:typography(value.typography),
      strokes:value.strokes.map(s=>{
        if(!plain(s)) fail("Trait invalide");
        return stroke(s.tool,s.width,s.points);
      }),
      created:value.created,updated:value.updated
    };
  }
  function empty() {return {format:FORMAT,notes:[]};}
  function validate(value) {
    if(!plain(value)||value.format!==FORMAT||!Array.isArray(value.notes)||
      value.notes.length>MAX_NOTES) fail("Format de carnet invalide");
    const ids=new Set();
    const notes=value.notes.map(n=>{
      const clean=note(n);
      if(ids.has(clean.id)) fail("Identifiant de note en double");
      ids.add(clean.id);
      return clean;
    });
    return {format:FORMAT,notes};
  }
  function upsert(book,value) {
    const source=validate(book);
    const clean=note(value);
    const index=source.notes.findIndex(n=>n.id===clean.id);
    if(index<0 && source.notes.length>=MAX_NOTES) fail("Carnet plein");
    if(index<0) source.notes.push(clean);
    else source.notes[index]=clean;
    return source;
  }
  function remove(book,id) {
    const source=validate(book);
    source.notes=source.notes.filter(n=>n.id!==id);
    return source;
  }
  function sorted(book,term) {
    const search=String(term||"").trim().toLocaleLowerCase("fr");
    return validate(book).notes.filter(n=>
      !search || (n.title+"\n"+n.text).toLocaleLowerCase("fr").includes(search)
    ).sort((a,b)=>b.updated.localeCompare(a.updated)||a.id.localeCompare(b.id));
  }
  function encode(book) {
    const serialized=JSON.stringify(validate(book),null,2);
    if(new TextEncoder().encode(serialized).byteLength>MAX_IMPORT_BYTES) {
      fail("Carnet trop volumineux pour cet export");
    }
    return serialized;
  }
  function decode(content) {
    if(typeof content!=="string") fail("Données importées invalides");
    if(new TextEncoder().encode(content).byteLength>MAX_IMPORT_BYTES) fail("Fichier trop volumineux");
    let parsed;
    try {parsed=JSON.parse(content);} catch(_) {fail("JSON invalide");}
    return validate(parsed);
  }
  function addStroke(n,s,now) {
    const clean=note(n);
    if(!date(now)) fail("Date invalide");
    if(clean.strokes.length>=MAX_STROKES) fail("Maximum de traits atteint");
    clean.strokes.push(stroke(s.tool,s.width,s.points));
    clean.updated=now;
    return clean;
  }
  function dropStroke(n,now) {
    const clean=note(n);
    if(clean.strokes.length){
      clean.strokes.pop();
      clean.updated=now;
    }
    return clean;
  }
  function safeFilename(title,extension) {
    const name=String(title||"note").normalize("NFKD")
      .replace(/[\u0300-\u036f]/g,"")
      .replace(/[^a-zA-Z0-9 _-]/g,"").trim().replace(/\s+/g,"-").slice(0,60);
    const ext=["txt","png","json"].includes(extension)?extension:"txt";
    return (name||"note")+"."+ext;
  }
  const API={FORMAT,MAX_NOTES,MAX_TITLE,MAX_TEXT,MAX_STROKES,MAX_POINTS,
    MAX_IMPORT_BYTES,PAGE,BRUSHES,FONTS,DEFAULT_TYPE,typography,point,stroke,blank,note,empty,validate,upsert,
    remove,sorted,encode,decode,addStroke,dropStroke,safeFilename};
  if(typeof module!=="undefined"&&module.exports)module.exports=API;
  if(root&&root.document)root.PMKBNotesCore=API;
})(typeof window!=="undefined"?window:null);
