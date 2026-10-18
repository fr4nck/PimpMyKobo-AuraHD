/* PMKB Notes V0.2 — browser adapter for the portable Notes core.
 * Deliberately no fetch(), external services, Kobo/SD I/O or app launcher integration.
 * Autosave is browser-local storage only; explicit JSON backup is essential.
 */
(function(){
  "use strict";
  const C=window.PMKBNotesCore,VK=window.PMKBVirtualKeyboard;
  if(!C||!VK)throw Error("PMKB Notes : modèle ou clavier manquant");
  const STORAGE="pmkb-notes-host-v1";
  const $=id=>document.getElementById(id);
  const refs={
    list:$("note-list"),search:$("search"),title:$("note-title"),text:$("note-text"),
    empty:$("empty-state"),editor:$("editor"),badge:$("save-status"),
    error:$("notes-error"),backupResult:$("backup-result"),
    count:$("note-count"),canvas:$("sketch"),screen:$("sketch-pane"),
    textPane:$("text-pane"),sketchPane:$("sketch-pane"),file:$("import-file"),
    tool:$("tool-label")
  };
  const ctx=refs.canvas.getContext("2d");
  const page=C.PAGE;
  let book=C.empty(),selected=null,pending=null,saving=null;
  let tab="text",tool="pen",width=5,drawing=null;
  // Short, session-only history of reversible operations. Native text undo remains native.
  const HISTORY_LIMIT=24,historyUndo=[],historyRedo=[];
  let storageEnabled=false,storageRevision=null;
  let feedbackTimer=null;
  const errors=new Map();
  const loadedFonts=new Map(); // FontFace objects are session-only; font files are never stored.
  const keyboardNode=$("virtual-keyboard"),keyboardRows=$("keyboard-rows");
  let keyboardPage="letters",keyboardUpper=false,keyboardTarget=null,lastEditable=refs.text;
  function keyboardVisible(){return !keyboardNode.hidden;}
  function hideKeyboard(){
    keyboardNode.hidden=true;
    keyboardTarget=null;
    $("toggle-keyboard").setAttribute("aria-expanded","false");
    document.body.classList.toggle("keyboard-open",false);
  }
  function keyboardLayout(){
    keyboardRows.replaceChildren();
    $("keyboard-label").textContent=keyboardPage==="letters"?"Clavier AZERTY":"Chiffres et symboles";
    for(const row of VK.rows(keyboardPage,keyboardUpper)){
      const line=document.createElement("div");line.className="keyboard-row";
      for(const key of row){
        const button=document.createElement("button");
        button.type="button";button.textContent=key.label;
        button.dataset.key=key.key;button.dataset.span=String(key.span);
        button.setAttribute("aria-label",key.aria);
        button.addEventListener("pointerdown",event=>event.preventDefault());
        button.addEventListener("click",()=>keyboardPress(key));
        line.appendChild(button);
      }
      keyboardRows.appendChild(line);
    }
  }
  function openKeyboard(){
    if(!current()||tab!=="text")return;
    keyboardTarget=[refs.title,refs.text].includes(document.activeElement)
      ?document.activeElement:lastEditable;
    if(![refs.title,refs.text].includes(keyboardTarget))keyboardTarget=refs.text;
    keyboardPage="letters";keyboardUpper=false;
    keyboardNode.hidden=false;
    $("toggle-keyboard").setAttribute("aria-expanded","true");
    document.body.classList.toggle("keyboard-open",true);
    keyboardLayout();
    keyboardTarget.focus();
  }
  function keyboardPress(key){
    if(keyboardNode.hidden||!current())return;
    if(key.key==="page"){
      keyboardPage=keyboardPage==="letters"?"symbols":"letters";
      keyboardLayout();return;
    }
    if(key.key==="shift"){
      keyboardUpper=!keyboardUpper;
      keyboardLayout();return;
    }
    const target=keyboardTarget===refs.title?refs.title:refs.text;
    const pressed=key.value===null?key.key:key.value;
    const result=VK.edit(target.value,target.selectionStart,target.selectionEnd,pressed,
      {maxLength:target===refs.title?C.MAX_TITLE:C.MAX_TEXT,multiline:target===refs.text});
    if(result.action==="next"){
      keyboardTarget=refs.text;lastEditable=refs.text;refs.text.focus();return;
    }
    if(result.blocked){
      status("Limite de longueur de la note atteinte.",true,"editing");return;
    }
    if(result.changed){
      target.value=result.value;
      if(target.setSelectionRange)target.setSelectionRange(result.start,result.end);
      target.dispatchEvent(new Event("input",{bubbles:true}));
    }
    target.focus();
    if(keyboardUpper&&key.value!==null){keyboardUpper=false;keyboardLayout();}
  }
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
    }catch(err){applyTypography();fontMessage.textContent="Taille refusée : choisir un nombre entre 12 et 36 px.";}
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
  function status(msg,warning,scope="action"){
    if(warning)errors.set(scope,msg);
    else errors.delete(scope);
    refs.error.textContent=[...errors.values()].join(" · ");
    refs.error.hidden=errors.size===0;
    if(scope==="storage")return;
    refs.backupResult.textContent=warning?"":msg;
    refs.backupResult.hidden=warning||!msg;
  }
  function saveStatus(msg,transient=false){
    clearTimeout(feedbackTimer);feedbackTimer=null;
    refs.badge.textContent=msg;
    refs.badge.dataset.symbol=msg==="En attente…"?"…":msg==="Enregistré"?"✓":msg?"!":"";
    refs.badge.hidden=!msg;
    if(transient)feedbackTimer=setTimeout(()=>saveStatus(""),2000);
  }
  const conflictMessage="Ce carnet a changé dans un autre onglet. Rien n'a été écrasé. Depuis Mes notes, exportez votre version en JSON avant de recharger ; l'import remplace le carnet et ne fusionne pas les modifications.";
  function storageConflict(){
    saveStatus("Non enregistré");
    status(conflictMessage,true,"storage");
  }
  function stored(){
    try {
      const existing=window.localStorage.getItem(STORAGE);
      // An empty string is corrupt stored JSON, not an empty notebook.
      if(existing!==null)book=C.decode(existing);
      else book=C.empty();
      storageRevision=existing;
      storageEnabled=true;
    }catch(error){
      book=C.empty();
      storageEnabled=false;
      saveStatus("Non enregistré");
      status("Stockage local inaccessible ou carnet illisible : conserver les données du navigateur et exporter les notes en JSON depuis Mes notes.",true,"storage");
    }
  }
  function persist(){
    clearTimeout(saving);saving=null;
    try{
      const value=C.encode(book);
      if(!storageEnabled)throw Error("Stockage local désactivé");
      // Optimistic stale-tab guard: do not overwrite an externally changed value.
      // This is not an atomic transaction and does not merge notebooks.
      if(window.localStorage.getItem(STORAGE)!==storageRevision){
        storageConflict();
        return false;
      }
      window.localStorage.setItem(STORAGE,value);
      storageRevision=value; // Only a successful write advances this tab's baseline.
      saveStatus("Enregistré",true);
      status("",false,"storage");
      return true;
    }catch(error){
      saveStatus("Non enregistré");
      status("Enregistrement local impossible : libérer du stockage ou exporter en JSON depuis Mes notes.",true,"storage");
      return false;
    }
  }
  function queueSave(){
    saveStatus("En attente…");
    clearTimeout(saving);
    saving=setTimeout(persist,350);
  }
  function flush(){if(saving!==null)persist();}
  function navigateWithSave(destination){
    if(book.notes.length || saving!==null || errors.has("storage")) {
      if(!persist() && !window.confirm("Enregistrement local impossible. Exportez le carnet en JSON depuis Mes notes avant de partir. Quitter quand même ?"))return;
    }
    hideKeyboard();
    window.location.assign(destination);
  }
  function quitNotes(){navigateWithSave("../launcher-v0/simulator.html");}
  function current(){return book.notes.find(n=>n.id===selected)||null;}
  function historyControls(){
    const canUndo=historyUndo.length>0,canRedo=historyRedo.length>0;
    for(const id of ["undo","undo-action"])$(id).disabled=!canUndo;
    for(const id of ["redo","redo-action"])$(id).disabled=!canRedo;
  }
  function recordAction(action){
    historyUndo.push(action);
    if(historyUndo.length>HISTORY_LIMIT)historyUndo.shift();
    historyRedo.length=0;
    historyControls();
  }
  function discardRedo(){
    if(!historyRedo.length)return;
    historyRedo.length=0;
    historyControls();
  }
  function resetHistory(){
    historyUndo.length=0;
    historyRedo.length=0;
    historyControls();
  }
  function sameStrokes(a,b){return JSON.stringify(a)===JSON.stringify(b);}
  function travelHistory(undo){
    const source=undo?historyUndo:historyRedo;
    if(!source.length)return;
    const action=source[source.length-1];
    const existing=book.notes.find(n=>n.id===action.noteId)||null;
    let restoreId=null,restoreTab="text";
    try {
      if(action.kind==="create"){
        if(undo){
          if(!existing)throw Error("Note absente");
          action.note=C.note(existing); // Redo restores text entered after creation.
          book=C.remove(book,action.noteId);
          restoreId=action.previousSelected;
          restoreTab=action.previousTab;
        }else{
          if(existing)throw Error("La note existe déjà");
          book=C.upsert(book,action.note);
          restoreId=action.noteId;
        }
      }else if(action.kind==="delete"){
        if(undo){
          if(existing)throw Error("Identifiant déjà utilisé");
          book=C.upsert(book,action.note);
          restoreId=action.noteId;
          restoreTab=action.previousTab;
        }else{
          if(!existing)throw Error("Note absente");
          book=C.remove(book,action.noteId);
        }
      }else if(action.kind==="stroke"){
        if(!existing)throw Error("Note absente");
        if(undo){
          if(!sameStrokes(existing.strokes.at(-1),action.stroke))
            throw Error("Le dernier trait a changé");
          book=C.upsert(book,C.dropStroke(existing,now()));
        }else{
          book=C.upsert(book,C.addStroke(existing,action.stroke,now()));
        }
        restoreId=action.noteId;restoreTab="sketch";
      }else if(action.kind==="clear-sketch"){
        if(!existing)throw Error("Note absente");
        const expected=undo?[]:action.strokes;
        if(!sameStrokes(existing.strokes,expected))
          throw Error("Le croquis a changé");
        book=C.upsert(book,C.note({...existing,
          strokes:undo?action.strokes:[],updated:now()}));
        restoreId=action.noteId;restoreTab="sketch";
      }else{
        throw Error("Action inconnue");
      }
    }catch(error){
      status("Impossible d'annuler ou de rétablir cette action : "+error.message+
        ". Les notes sont conservées.",true,"history");
      return;
    }
    source.pop();
    (undo?historyRedo:historyUndo).push(action);
    historyControls();
    drawing=null;
    queueSave();
    if(restoreId && book.notes.some(n=>n.id===restoreId)){
      showEditor(restoreId);
      setTab(restoreTab);
    }else{
      selected=null;
      refs.editor.hidden=true;refs.empty.hidden=false;
      renderList();
    }
    if(errors.has("history"))status("",false,"history");
  }
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
    const previousSelected=selected,previousTab=tab;
    replace(item);
    recordAction({kind:"create",noteId:item.id,note:item,previousSelected,previousTab});
    refs.search.value="";
    showEditor(item.id);
    refs.title.focus();
    refs.title.select();
  }
  function duplicateCurrent(){
    const original=current();
    if(!original)return;
    flush();
    if(book.notes.length>=C.MAX_NOTES){
      status("Limite de 100 notes atteinte : duplication impossible.",true);return;
    }
    const timestamp=now(),previousSelected=selected,previousTab=tab;
    const copy=C.note({...original,id:uniqueId(),
      title:("Copie de "+original.title).slice(0,C.MAX_TITLE),
      created:timestamp,updated:timestamp});
    replace(copy);
    recordAction({kind:"create",noteId:copy.id,note:copy,previousSelected,previousTab});
    refs.search.value="";
    showEditor(copy.id);
    refs.title.focus();
  }
  function showEditor(id){
    hideKeyboard();
    flush();
    const item=book.notes.find(n=>n.id===id);
    if(!item)return;
    selected=id;drawing=null;
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
      discardRedo(); // Fresh text/typography changes invalidate the redo branch.
      renderList();
      if(errors.has("editing"))status("",false,"editing");
    }catch(err){
      const message=Object.prototype.hasOwnProperty.call(patch,"title")
        ?"Titre requis (100 caractères maximum)."
        :Object.prototype.hasOwnProperty.call(patch,"text")
        ?"Texte trop long (120 000 caractères maximum)."
        :"Modification refusée : "+err.message;
      status(message,true,"editing");
    }
  }
  function renderList(){
    $("toggle-keyboard").disabled=!current()||tab!=="text";
    $("duplicate-note").disabled=!current()||book.notes.length>=C.MAX_NOTES;
    $("delete-note").disabled=!current();
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
    if(next==="sketch")hideKeyboard();
    tab=next;
    const isSketch=tab==="sketch";
    refs.textPane.hidden=isSketch;
    refs.sketchPane.hidden=!isSketch;
    $("export-txt").hidden=isSketch;
    $("export-png").hidden=!isSketch;
    $("tab-text").classList.toggle("active",!isSketch);
    $("tab-sketch").classList.toggle("active",isSketch);
    $("tab-text").setAttribute("aria-selected",isSketch?"false":"true");
    $("tab-sketch").setAttribute("aria-selected",isSketch?"true":"false");
    $("tab-text").tabIndex=isSketch?-1:0;
    $("tab-sketch").tabIndex=isSketch?0:-1;
    $("toggle-keyboard").disabled=isSketch||!current();
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
    try{
      const updated=C.addStroke(current(),finished,now());
      replace(updated);
      recordAction({kind:"stroke",noteId:updated.id,
        stroke:C.stroke(finished.tool,finished.width,finished.points)});
    }catch(error){status("Croquis : "+error.message,true);}
    renderDrawing();
  }
  function cancel(){drawing=null;renderDrawing();}
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
      selected=null;drawing=null;
      hideKeyboard();
      resetHistory(); // A notebook replacement invalidates all prior undo targets.
      refs.editor.hidden=true;refs.empty.hidden=false;
      toggleDrawer(false);
      renderList();
      status("Import effectué.",false);
    }catch(err){status("Import refusé : "+err.message,true);}
  }
  function deleteCurrent(){
    const item=current();if(!item)return;
    if(!window.confirm("Supprimer définitivement « "+item.title+" » de ce navigateur ?"))return;
    const snapshot=C.note(item),previousTab=tab;
    book=C.remove(book,item.id);selected=null;drawing=null;
    hideKeyboard();
    recordAction({kind:"delete",noteId:item.id,note:snapshot,previousTab});
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
  refs.title.addEventListener("focus",()=>{lastEditable=refs.title;keyboardTarget=refs.title;});
  refs.text.addEventListener("focus",()=>{lastEditable=refs.text;keyboardTarget=refs.text;});
  refs.title.addEventListener("input",()=>update({title:refs.title.value||"Sans titre"}));
  refs.title.addEventListener("blur",()=>{
    if(!refs.title.value.trim()){
      refs.title.value="Sans titre";
      update({title:refs.title.value});
    }
  });
  refs.text.addEventListener("input",()=>update({text:refs.text.value}));
  refs.search.addEventListener("input",renderList);
  $("new-note").addEventListener("click",create);
  $("toolbar-new").addEventListener("click",create);
  openNotes.addEventListener("click",()=>toggleDrawer(drawer.hidden));
  $("close-drawer").addEventListener("click",()=>toggleDrawer(false));
  backdrop.addEventListener("click",()=>toggleDrawer(false));
  document.addEventListener("keydown",event=>{
    const key=typeof event.key==="string"?event.key.toLowerCase():"";
    if((event.ctrlKey||event.metaKey)&&!event.altKey&&(key==="z"||key==="y")){
      const target=event.target;
      // Do not hijack the browser's native undo/redo for typing and form inputs.
      if(target===refs.text||target===refs.title||target===refs.search||
         target===fontSize||target===fontFamily||
         target?.isContentEditable||
         ["input","textarea","select"].includes(target?.tagName?.toLowerCase()))return;
      const isRedo=(key==="z"&&event.shiftKey)||(key==="y"&&!event.shiftKey);
      const isUndo=(key==="z"&&!event.shiftKey);
      if((isRedo&&historyRedo.length)||(isUndo&&historyUndo.length)){
        event.preventDefault();
        travelHistory(isUndo);
      }
      return;
    }
    if(event.key!=="Escape")return;
    if(keyboardVisible()){event.preventDefault();hideKeyboard();}
    else if(!fontPanel.hidden) {
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
  $("duplicate-note").addEventListener("click",duplicateCurrent);
  $("toggle-keyboard").addEventListener("click",()=>{
    if(keyboardVisible())hideKeyboard();else openKeyboard();
  });
  $("open-calculator").addEventListener("click",()=>navigateWithSave("../calculator-v01/index.html"));
  $("keyboard-close").addEventListener("click",hideKeyboard);
  $("undo-action").addEventListener("click",()=>travelHistory(true));
  $("redo-action").addEventListener("click",()=>travelHistory(false));
  $("save-now").addEventListener("click",persist);
  $("quit-notes").addEventListener("click",quitNotes);
  $("tab-text").addEventListener("click",()=>setTab("text"));
  $("tab-sketch").addEventListener("click",()=>setTab("sketch"));
  function onTabKey(event){
    const next=event.key==="Home"?"text":event.key==="End"?"sketch":
      (event.key==="ArrowLeft"||event.key==="ArrowRight")
        ?(tab==="text"?"sketch":"text"):null;
    if(!next)return;
    event.preventDefault();
    setTab(next);
    $(next==="text"?"tab-text":"tab-sketch").focus();
  }
  $("tab-text").addEventListener("keydown",onTabKey);
  $("tab-sketch").addEventListener("keydown",onTabKey);
  for(const el of document.querySelectorAll("[data-tool]")){
    el.addEventListener("click",()=>{
      tool=el.dataset.tool;
      for(const b of document.querySelectorAll("[data-tool]")){
        b.classList.toggle("active",b===el);
        b.setAttribute("aria-pressed",b===el?"true":"false");
      }
      refs.tool.textContent=tool==="pen"?"Crayon":"Gomme";
    });
  }
  for(const el of document.querySelectorAll("[data-width]")){
    el.addEventListener("click",()=>{
      width=Number(el.dataset.width);
      for(const b of document.querySelectorAll("[data-width]")){
        b.classList.toggle("active",b===el);
        b.setAttribute("aria-pressed",b===el?"true":"false");
      }
    });
  }
  $("undo").addEventListener("click",()=>travelHistory(true));
  $("redo").addEventListener("click",()=>travelHistory(false));
  $("clear-sketch").addEventListener("click",()=>{
    const item=current();
    if(item && item.strokes.length && window.confirm("Effacer le croquis de cette note ?")){
      const strokes=item.strokes.map(s=>C.stroke(s.tool,s.width,s.points));
      replace(C.note({...item,strokes:[],updated:now()}));
      recordAction({kind:"clear-sketch",noteId:item.id,strokes});
      renderDrawing();
    }
  });
  $("export-json").addEventListener("click",exportBackup);
  $("export-txt").addEventListener("click",exportText);
  $("export-png").addEventListener("click",exportPng);
  $("import-button").addEventListener("click",()=>refs.file.click());
  refs.file.addEventListener("change",importBackup);
  window.addEventListener("pagehide",flush);
  window.addEventListener("storage",event=>{
    if(event.storageArea!==window.localStorage ||
       (event.key!==STORAGE && event.key!==null) ||
       event.newValue===storageRevision)return;
    // Keep pending edits in memory for export; never flush a stale save.
    clearTimeout(saving);saving=null;
    storageConflict();
  });
  stored();
  historyControls();
  renderList();
  renderDrawing();
  const mostRecent=C.sorted(book)[0];
  if(mostRecent)showEditor(mostRecent.id);
  else applyTypography();
})();
