/* PMKB Notes V0.2 — browser adapter for the portable Notes core.
 * Deliberately no fetch(), external services, Kobo/SD I/O or app launcher integration.
 * Autosave is browser-local storage only; explicit JSON backup is essential.
 */
(function(){
  "use strict";
  const C=window.PMKBNotesCore;
  if(!C)throw Error("PMKBNotesCore absent");
  const STORAGE="pmkb-notes-host-v1";
  const $=id=>document.getElementById(id);
  const refs={
    list:$("note-list"),search:$("search"),title:$("note-title"),text:$("note-text"),
    empty:$("empty-state"),editor:$("editor"),badge:$("save-status"),
    count:$("note-count"),canvas:$("sketch"),screen:$("sketch-pane"),
    textPane:$("text-pane"),sketchPane:$("sketch-pane"),file:$("import-file"),
    tool:$("tool-label")
  };
  const ctx=refs.canvas.getContext("2d");
  const page=C.PAGE;
  let book=C.empty(),selected=null,pending=null,saving=null;
  let tab="text",tool="pen",width=5,drawing=null,redo=[];
  let storageEnabled=false;
  const loadedFonts=new Map(); // FontFace objects are session-only; font files are never stored.
  const fontNames={
    mono:'ui-monospace,Consolas,"DejaVu Sans Mono",monospace',
    sans:'"Noto Sans","Liberation Sans",Arial,sans-serif',
    serif:'"Noto Serif","Liberation Serif",Georgia,serif',
    handwriting:'"URW Chancery L","Comic Sans MS",cursive'
  };
  const fontFamily=$("font-family"), fontSize=$("font-size"),
    fontFile=$("font-file"),fontMessage=$("font-message");
  const fontPanel=$("font-options"),fontToggle=$("open-fonts"),fontContainer=$("type-menu");
  function toggleTypography(open) {
    fontPanel.hidden=!open;
    fontToggle.setAttribute("aria-expanded",open?"true":"false");
    if(open) fontFamily.focus();
    else if(fontPanel.contains(document.activeElement))fontToggle.focus();
  }
  const drawer=$("notes-drawer"),backdrop=$("drawer-backdrop"),openNotes=$("open-notes");

  function toggleDrawer(open) {
    drawer.hidden=!open;
    backdrop.hidden=!open;
    openNotes.setAttribute("aria-expanded",open?"true":"false");
    if(open) {
      refs.search.focus();
    } else if(drawer.contains(document.activeElement)) {
      openNotes.focus();
    }
  }
  function fontSignature(bytes) {
    if(bytes.length<4)return null;
    const magic=String.fromCharCode(bytes[0],bytes[1],bytes[2],bytes[3]);
    if(magic==="OTTO")return "otf";
    if(magic==="wOFF")return "woff";
    if(magic==="wOF2")return "woff2";
    if(magic==="true" || magic==="typ1" ||
       (bytes[0]===0 && bytes[1]===1 && bytes[2]===0 && bytes[3]===0))return "ttf";
    return null;
  }
  function renderFontOptions(activeId) {
    for(const opt of [...fontFamily.options]) {
      if(opt.value.startsWith("import:"))opt.remove();
    }
    for(const [id,entry] of loadedFonts) {
      const option=document.createElement("option");
      option.value=id;
      option.textContent="Importée : "+entry.name;
      fontFamily.appendChild(option);
    }
    if(activeId.startsWith("import:") && !loadedFonts.has(activeId)) {
      const option=document.createElement("option");
      option.value=activeId;
      option.textContent="Police importée absente — réimporter";
      fontFamily.appendChild(option);
    }
  }
  function applyTypography() {
    const item=current();
    const style=item?C.typography(item.typography):C.typography();
    renderFontOptions(style.font);
    fontFamily.value=style.font;
    fontSize.value=String(style.size);
    const imported=loadedFonts.get(style.font);
    refs.text.style.fontFamily=imported
      ? '"'+imported.family+'",monospace'
      : (fontNames[style.font] || fontNames.mono);
    refs.text.style.fontSize=style.size+"px";
    refs.text.style.lineHeight=String(style.lineHeight);
    if(style.font.startsWith("import:") && !imported) {
      fontMessage.textContent="Police importée absente : réimporte le fichier pour retrouver son rendu. Texte intact.";
    } else {
      fontMessage.textContent="Polices personnalisées en mémoire pendant cette session uniquement ; le JSON garde la préférence, pas le fichier de police.";
    }
  }
  function changeTypography() {
    const item=current();if(!item)return;
    const next={
      font:fontFamily.value,
      size:Number(fontSize.value),
      lineHeight:C.typography(item.typography).lineHeight
    };
    try{
      update({typography:C.typography(next)});
      applyTypography();
    }catch(err){applyTypography();status(err.message,true);}
  }
  async function importFont(event) {
    const file=event.target.files[0];fontFile.value="";
    if(!file)return;
    const ext=(file.name.split(".").pop()||"").toLowerCase();
    if(!["ttf","otf","woff","woff2"].includes(ext)||file.size<12||file.size>2000000){
      fontMessage.textContent="Fichier refusé : TTF, OTF, WOFF ou WOFF2 de 2 Mo maximum.";
      return;
    }
    if(!window.FontFace || !window.crypto?.subtle) {
      fontMessage.textContent="Ce navigateur ne permet pas cet import local de polices.";
      return;
    }
    try {
      const bytes=await file.arrayBuffer();
      if(fontSignature(new Uint8Array(bytes))!==ext)throw Error("Format de police non conforme");
      const digest=new Uint8Array(await window.crypto.subtle.digest("SHA-256",bytes));
      const id="import:"+Array.from(digest.slice(0,6),n=>n.toString(16).padStart(2,"0")).join("");
      if(!loadedFonts.has(id)) {
        const family="PMKBFont"+id.slice(7);
        const face=new FontFace(family,bytes);
        await face.load();
        document.fonts.add(face);
        loadedFonts.set(id,{family,name:file.name,face});
      }
      renderFontOptions(id);
      if(current())update({typography:{...current().typography,font:id}});
      applyTypography();
      fontMessage.textContent="Police chargée pour cette session : "+file.name+
        ". La sauvegarde JSON ne contient pas le fichier ; conserve une copie.";
    }catch(error){
      fontMessage.textContent="Import impossible : format non pris en charge ou fichier invalide.";
    }
  }

  function now(){return new Date().toISOString();}
  function status(msg,warning){
    refs.badge.textContent=msg;
    refs.badge.classList.toggle("warning",Boolean(warning));
  }
  function stored(){
    try {
      const existing=window.localStorage.getItem(STORAGE);
      storageEnabled=true;
      if(existing)book=C.decode(existing);
      else book=C.empty();
    }catch(error){
      book=C.empty();
      storageEnabled=false;
      status("Stockage du navigateur indisponible : exporter les notes en JSON",true);
    }
  }
  function persist(){
    clearTimeout(saving);saving=null;
    try{
      const value=C.encode(book);
      if(!storageEnabled)throw Error("Stockage local désactivé");
      window.localStorage.setItem(STORAGE,value);
      status("Enregistré dans ce navigateur · exporter pour sauvegarder",false);
      return true;
    }catch(error){
      status("Sauvegarde auto indisponible : exporter en JSON !",true);
      return false;
    }
  }
  function queueSave(){
    status("Modification en attente…",false);
    clearTimeout(saving);
    saving=setTimeout(persist,350);
  }
  function flush(){if(saving!==null)persist();}
  function current(){return book.notes.find(n=>n.id===selected)||null;}
  function replace(note){
    book=C.upsert(book,note);
    selected=note.id;
    queueSave();
  }
  function uniqueId(){
    let id;
    do{id="n"+Date.now().toString(36)+Math.random().toString(36).slice(2,9);}
    while(book.notes.some(n=>n.id===id));
    return id;
  }
  function create(){
    flush();
    if(book.notes.length>=C.MAX_NOTES){status("Limite de 100 notes atteinte",true);return;}
    const item=C.blank(uniqueId(),now());
    replace(item);
    redo=[];
    refs.search.value="";
    showEditor(item.id);
    refs.title.focus();
    refs.title.select();
  }
  function showEditor(id){
    flush();
    const item=book.notes.find(n=>n.id===id);
    if(!item)return;
    selected=id;redo=[];drawing=null;
    refs.empty.hidden=true;refs.editor.hidden=false;
    refs.title.value=item.title;
    refs.text.value=item.text;
    setTab("text");
    toggleTypography(false);
    applyTypography();
    toggleDrawer(false);
    renderList();
  }
  function update(patch){
    const old=current();
    if(!old)return;
    try {
      const next=C.note(Object.assign({},old,patch,{updated:now()}));
      replace(next);
      renderList();
    }catch(err){status("Édition refusée : "+err.message,true);}
  }
  function renderList(){
    refs.list.replaceChildren();
    const found=C.sorted(book,refs.search.value);
    refs.count.textContent=book.notes.length+" / "+C.MAX_NOTES;
    for(const item of found){
      const btn=document.createElement("button");
      btn.type="button";
      btn.className="note-item";
      btn.classList.toggle("chosen",item.id===selected);
      btn.setAttribute("aria-pressed",item.id===selected?"true":"false");
      const heading=document.createElement("strong");heading.textContent=item.title;
      const desc=document.createElement("small");
      const preview=item.text.trim().replace(/\s+/g," ").slice(0,78);
      desc.textContent=preview || (item.strokes.length?"Croquis · "+item.strokes.length+" trait(s)":"Note vide");
      btn.append(heading,desc);
      btn.addEventListener("click",()=>showEditor(item.id));
      refs.list.appendChild(btn);
    }
    if(!found.length){
      const p=document.createElement("p");p.className="no-match";p.textContent="Aucune note correspondante.";
      refs.list.appendChild(p);
    }
  }
  function setTab(next){
    tab=next;
    const isSketch=tab==="sketch";
    refs.textPane.hidden=isSketch;
    refs.sketchPane.hidden=!isSketch;
    $("tab-text").classList.toggle("active",!isSketch);
    $("tab-sketch").classList.toggle("active",isSketch);
    $("tab-text").setAttribute("aria-selected",isSketch?"false":"true");
    $("tab-sketch").setAttribute("aria-selected",isSketch?"true":"false");
    if(isSketch) {
      toggleTypography(false);
      renderDrawing();
    }
  }
  function drawStroke(stroke){
    const pts=stroke.points;
    if(!pts.length)return;
    ctx.strokeStyle=stroke.tool==="eraser"?"#ffffff":"#111111";
    ctx.fillStyle=ctx.strokeStyle;
    ctx.lineWidth=stroke.width;
    ctx.lineJoin="round";ctx.lineCap="round";
    if(pts.length===1){
      ctx.beginPath();ctx.arc(pts[0][0],pts[0][1],stroke.width/2,0,Math.PI*2);ctx.fill();return;
    }
    ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);
    for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);
    ctx.stroke();
  }
  function renderDrawing(){
    ctx.fillStyle="#ffffff";
    ctx.fillRect(0,0,page.width,page.height);
    const item=current();
    if(item)for(const s of item.strokes)drawStroke(s);
    if(drawing)drawStroke(drawing);
    $("stroke-count").textContent=(item?item.strokes.length:0)+" / "+C.MAX_STROKES+" traits";
  }
  function coordinate(event){
    const rect=refs.canvas.getBoundingClientRect();
    return C.point((event.clientX-rect.left)*page.width/rect.width,
      (event.clientY-rect.top)*page.height/rect.height);
  }
  function down(event){
    if(event.button!==0 && event.pointerType==="mouse")return;
    if(!current())return;
    if(current().strokes.length>=C.MAX_STROKES){
      status("Limite de traits atteinte : exporter ou effacer",true);return;
    }
    event.preventDefault();
    redo=[];
    drawing={tool,width,points:[coordinate(event)]};
    if(refs.canvas.setPointerCapture)refs.canvas.setPointerCapture(event.pointerId);
    renderDrawing();
  }
  function move(event){
    if(!drawing)return;
    event.preventDefault();
    const next=coordinate(event),p=drawing.points.at(-1);
    if((next[0]!==p[0]||next[1]!==p[1])&&drawing.points.length<C.MAX_POINTS){
      drawing.points.push(next);
    }
    renderDrawing();
  }
  function up(event){
    if(!drawing)return;
    event.preventDefault();
    const finished=drawing;drawing=null;
    try{replace(C.addStroke(current(),finished,now()));}
    catch(error){status("Croquis : "+error.message,true);}
    renderDrawing();
  }
  function cancel(){drawing=null;renderDrawing();}
  function undoStroke(){
    const item=current();if(!item||!item.strokes.length)return;
    redo.push(item.strokes[item.strokes.length-1]);
    replace(C.dropStroke(item,now()));
    renderDrawing();
  }
  function redoStroke(){
    if(!current()||!redo.length)return;
    const s=redo.pop();
    try{replace(C.addStroke(current(),s,now()));}
    catch(err){status("Rétablissement impossible",true);}
    renderDrawing();
  }
  function download(filename,blob){
    const url=URL.createObjectURL(blob);
    const anchor=document.createElement("a");
    anchor.href=url;anchor.download=filename;
    document.body.appendChild(anchor);anchor.click();anchor.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function exportBackup(){
    flush();
    try{
      const json=C.encode(book);
      download("PMKB-Notes-sauvegarde.json",new Blob([json],{type:"application/json;charset=utf-8"}));
      status("Sauvegarde JSON téléchargée : conserve ce fichier",false);
    }catch(err){status(err.message,true);}
  }
  function exportText(){
    const item=current();if(!item)return;
    flush();
    const content=item.title+"\n\n"+item.text;
    download(C.safeFilename(item.title,"txt"),
      new Blob([content],{type:"text/plain;charset=utf-8"}));
  }
  function exportPng(){
    const item=current();if(!item)return;
    renderDrawing();
    refs.canvas.toBlob(blob=>{
      if(blob)download(C.safeFilename(item.title,"png"),blob);
      else status("Export PNG impossible",true);
    },"image/png");
  }
  async function importBackup(event){
    const file=event.target.files[0];refs.file.value="";
    if(!file)return;
    if(file.size>C.MAX_IMPORT_BYTES){status("Sauvegarde JSON trop volumineuse",true);return;}
    try{
      const candidate=C.decode(await file.text());
      if(!window.confirm("Remplacer toutes les notes du navigateur par les "+candidate.notes.length+
        " note(s) du fichier ? Exporter d'abord les notes actuelles !"))return;
      flush();
      const oldBook=book;
      book=candidate;
      if(!persist()){
        book=oldBook;
        status("Import non enregistré : carnet précédent conservé",true);
        return;
      }
      selected=null;redo=[];drawing=null;
      refs.editor.hidden=true;refs.empty.hidden=false;
      toggleDrawer(false);
      renderList();
      status("Import effectué. Sauvegarde dans ce navigateur uniquement.",false);
    }catch(err){status("Import refusé : "+err.message,true);}
  }
  function deleteCurrent(){
    const item=current();if(!item)return;
    if(!window.confirm("Supprimer définitivement « "+item.title+" » de ce navigateur ?"))return;
    book=C.remove(book,item.id);selected=null;redo=[];drawing=null;
    refs.editor.hidden=true;refs.empty.hidden=false;
    queueSave();renderList();
  }

  refs.canvas.width=page.width;refs.canvas.height=page.height;
  refs.canvas.addEventListener("pointerdown",down);
  refs.canvas.addEventListener("pointermove",move);
  refs.canvas.addEventListener("pointerup",up);
  refs.canvas.addEventListener("pointercancel",cancel);
  refs.canvas.addEventListener("lostpointercapture",()=>{if(drawing)cancel();});
  refs.title.maxLength=C.MAX_TITLE;refs.text.maxLength=C.MAX_TEXT;
  refs.title.addEventListener("input",()=>update({title:refs.title.value||"Sans titre"}));
  refs.text.addEventListener("input",()=>update({text:refs.text.value}));
  refs.search.addEventListener("input",renderList);
  $("new-note").addEventListener("click",create);
  $("toolbar-new").addEventListener("click",create);
  openNotes.addEventListener("click",()=>toggleDrawer(drawer.hidden));
  $("close-drawer").addEventListener("click",()=>toggleDrawer(false));
  backdrop.addEventListener("click",()=>toggleDrawer(false));
  document.addEventListener("keydown",event=>{
    if(event.key!=="Escape")return;
    if(!fontPanel.hidden) {
      event.preventDefault();
      toggleTypography(false);
    } else if(!drawer.hidden) {
      event.preventDefault();
      toggleDrawer(false);
    }
  });
  document.addEventListener("pointerdown",event=>{
    if(!fontPanel.hidden && !fontContainer.contains(event.target)) {
      toggleTypography(false);
    }
  });
  fontToggle.addEventListener("click",()=>toggleTypography(fontPanel.hidden));
  fontFamily.addEventListener("change",changeTypography);
  fontSize.addEventListener("change",changeTypography);
  $("import-font").addEventListener("click",()=>fontFile.click());
  fontFile.addEventListener("change",importFont);
  $("delete-note").addEventListener("click",deleteCurrent);
  $("save-now").addEventListener("click",persist);
  $("tab-text").addEventListener("click",()=>setTab("text"));
  $("tab-sketch").addEventListener("click",()=>setTab("sketch"));
  for(const el of document.querySelectorAll("[data-tool]")){
    el.addEventListener("click",()=>{
      tool=el.dataset.tool;
      for(const b of document.querySelectorAll("[data-tool]"))b.classList.toggle("active",b===el);
      refs.tool.textContent=tool==="pen"?"Crayon":"Gomme";
    });
  }
  for(const el of document.querySelectorAll("[data-width]")){
    el.addEventListener("click",()=>{
      width=Number(el.dataset.width);
      for(const b of document.querySelectorAll("[data-width]"))b.classList.toggle("active",b===el);
    });
  }
  $("undo").addEventListener("click",undoStroke);
  $("redo").addEventListener("click",redoStroke);
  $("clear-sketch").addEventListener("click",()=>{
    const item=current();
    if(item && item.strokes.length && window.confirm("Effacer le croquis de cette note ?")){
      replace(C.note({...item,strokes:[],updated:now()}));
      redo=[];renderDrawing();
    }
  });
  $("export-json").addEventListener("click",exportBackup);
  $("export-txt").addEventListener("click",exportText);
  $("export-png").addEventListener("click",exportPng);
  $("import-button").addEventListener("click",()=>refs.file.click());
  refs.file.addEventListener("change",importBackup);
  window.addEventListener("pagehide",flush);
  stored();
  renderList();
  renderDrawing();
  const mostRecent=C.sorted(book)[0];
  if(mostRecent)showEditor(mostRecent.id);
  else applyTypography();
  if(!book.notes.length)status("Carnet vide. Crée une note et exporte une sauvegarde JSON.",!storageEnabled);
  else if(storageEnabled)status("Notes locales chargées · export JSON conseillé",false);
})();
