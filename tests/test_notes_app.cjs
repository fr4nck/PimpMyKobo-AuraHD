/* Exercise the real browser adapter with isolated DOM/storage/timer fixtures. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const C = require('../experimental/notes-v01/notes-core.js');
const app = path.join(__dirname, '../experimental/notes-v01');

function browser({readError=false, initial=null, confirmReply=true, sharedStorage=null}={}) {
  const elements = new Map(), timers = new Map(), downloads = [], blobs = [];
  const events = new Map(), documentEvents = new Map();
  const store = sharedStorage || {value:initial};
  let serial=0, writeError=false, destination=null;
  function element(id='') {
    return {id, hidden:false, value:'', textContent:'', style:{}, options:[], files:[],
      dataset:{}, children:[], listeners:{}, attrs:{},
      classList:{toggle(){}},
      addEventListener(name, callback){this.listeners[name]=callback;},
      setAttribute(name,value){this.attrs[name]=value;},
      append(...items){this.children.push(...items);},
      appendChild(item){this.children.push(item);},
      replaceChildren(){this.children=[];},
      focus(){document.activeElement=this;}, select(){}, contains(target){return target===this;},
      click(){if(this.download)downloads.push(this.download); return this.listeners.click?.({target:this});},
      remove(){}, toBlob(callback){callback(new Blob(['synthetic PNG'],{type:'image/png'}));},
      getBoundingClientRect(){return {left:0,top:0,width:900,height:600};},
      getContext(){return {fillRect(){},beginPath(){},arc(){},fill(){},moveTo(){},lineTo(){},stroke(){}}}
    };
  }
  const html=fs.readFileSync(path.join(app,'index.html'),'utf8');
  for(const match of html.matchAll(/<[^>]+id="([^"]+)"[^>]*>/g)) {
    const item=element(match[1]); item.hidden=/\bhidden\b/.test(match[0]); elements.set(item.id,item);
  }
  const document={activeElement:null, body:element(), fonts:{add(){}},
    getElementById:id=>elements.get(id), createElement:()=>element(),
    querySelectorAll:()=>[],
    addEventListener(type,fn){documentEvents.set(type,fn);}};
  const window={PMKBNotesCore:C, confirm:()=>confirmReply,
    addEventListener(type, callback){events.set(type,callback);},
    location:{assign(url){destination=url;}},
    localStorage:{getItem(){if(readError)throw Error('blocked');return store.value;},
      setItem(key,value){if(writeError)throw Error('quota');store.value=value;}}};
  vm.runInNewContext(fs.readFileSync(path.join(app,'notes-app.js'),'utf8'),{
    window,document,Blob,URL:{createObjectURL:blob=>{blobs.push(blob);return 'blob:test';},revokeObjectURL(){}},
    setTimeout(callback){timers.set(++serial,callback);return serial;},
    clearTimeout(id){timers.delete(id);},console
  });
  return {get:id=>elements.get(id), downloads, blobs, stored:()=>store.value,
    destination:()=>destination, active:()=>document.activeElement,
    key(key,options={}){
      const event={key,ctrlKey:false,metaKey:false,shiftKey:false,altKey:false,
        target:document.body,preventDefault(){this.defaultPrevented=true;},...options};
      documentEvents.get('keydown')(event);
      return event;
    },
    signalStorage(newValue,key='pmkb-notes-host-v1'){
      events.get('storage')?.({key,newValue,storageArea:window.localStorage});
    },
    failWrites(value){writeError=value;},
    event(id,name,params={}){const item=elements.get(id);
      return item.listeners[name]({target:item,currentTarget:item,preventDefault(){this.defaultPrevented=true;},...params});},
    tick(){const jobs=[...timers.values()];timers.clear();for(const job of jobs)job();}};
}

test('idle status occupies no space; pending and saved feedback is temporary',()=>{
  const b=browser();
  assert.equal(b.get('save-status').textContent,'');
  assert.equal(b.get('save-status').hidden,true);
  assert.equal(b.get('notes-error').hidden,true);
  assert.equal(b.get('backup-result').hidden,true);
  b.event('toolbar-new','click');
  assert.equal(b.get('save-status').textContent,'Enregistré');
  assert.equal(b.get('save-status').hidden,false);
  b.get('note-text').value='Texte conservé';b.event('note-text','input');
  assert.equal(b.get('save-status').textContent,'En attente…');
  assert.equal(b.get('save-status').hidden,false);
  b.tick();
  assert.equal(C.decode(b.stored()).notes[0].text,'Texte conservé');
  assert.equal(b.get('save-status').textContent,'Enregistré');
  b.tick();
  assert.equal(b.get('save-status').hidden,true);
  assert.equal(b.get('save-status').textContent,'');
  assert.equal(b.get('notes-error').hidden,true);
});

test('loading existing notes has no permanent toolbar status',()=>{
  const book=C.upsert(C.empty(),C.blank('existing','2026-10-14T08:00:00.000Z'));
  const b=browser({initial:C.encode(book)});
  assert.equal(b.get('save-status').hidden,true);
  assert.equal(b.get('save-status').textContent,'');
});

test('quit saves pending edits before returning to the host launcher',()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-text').value='Avant de quitter';b.event('note-text','input');
  b.event('quit-notes','click');
  assert.equal(C.decode(b.stored()).notes[0].text,'Avant de quitter');
  assert.equal(b.destination(),'../launcher-v0/simulator.html');
});

test('failed save requires an explicit choice before quitting',()=>{
  for(const confirmReply of [false,true]) {
    const b=browser({confirmReply});b.event('toolbar-new','click');b.failWrites(true);
    b.get('note-text').value='En mémoire';b.event('note-text','input');
    b.event('quit-notes','click');
    assert.equal(b.destination(),confirmReply?'../launcher-v0/simulator.html':null);
    assert.equal(b.get('note-text').value,'En mémoire');
    assert.equal(b.get('notes-error').hidden,false);
  }
});

test('header export follows Text or Sketch mode and keeps both download formats',()=>{
  const b=browser();b.event('toolbar-new','click');
  assert.equal(b.get('export-txt').hidden,false);
  assert.equal(b.get('export-png').hidden,true);
  b.event('export-txt','click');
  assert.match(b.downloads[0],/\.txt$/);
  b.event('tab-sketch','click');
  assert.equal(b.get('export-txt').hidden,true);
  assert.equal(b.get('export-png').hidden,false);
  b.event('export-png','click');
  assert.match(b.downloads[1],/\.png$/);
  b.event('tab-text','click');
  assert.equal(b.get('export-txt').hidden,false);
  assert.equal(b.get('export-png').hidden,true);
});

test('write failure stays visible through JSON export; successful retry clears it',()=>{
  const b=browser();b.event('toolbar-new','click');b.failWrites(true);
  b.get('note-text').value='À sauvegarder';b.event('note-text','input');b.tick();
  assert.equal(b.get('save-status').textContent,'Non enregistré');
  assert.equal(b.get('notes-error').hidden,false);
  b.tick();
  assert.equal(b.get('save-status').hidden,false);
  assert.match(b.get('notes-error').textContent,/exporter en JSON/);
  b.event('export-json','click');
  assert.deepEqual(b.downloads,['PMKB-Notes-sauvegarde.json']);
  assert.equal(b.get('save-status').textContent,'Non enregistré');
  assert.equal(b.get('notes-error').hidden,false);
  b.failWrites(false);b.event('save-now','click');
  assert.equal(b.get('notes-error').hidden,true);
  assert.equal(C.decode(b.stored()).notes[0].text,'À sauvegarder');
});

test('blocked or corrupt storage is reported even with an empty notebook',()=>{
  for(const options of [{readError:true},{initial:'invalid JSON'}]) {
    const b=browser(options);
    assert.equal(b.get('save-status').textContent,'Non enregistré');
    assert.equal(b.get('notes-error').hidden,false);
    b.event('save-now','click');
    assert.equal(b.stored(),options.initial??null);
  }
});

test('autosave does not erase an invalid-import error; valid import clears it',async()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-text').value='Original';b.event('note-text','input');
  b.get('import-file').files=[{size:10,text:async()=>'{invalid'}];
  await b.event('import-file','change');
  assert.match(b.get('notes-error').textContent,/Import refusé/);
  b.tick();
  assert.equal(b.get('notes-error').hidden,false);
  assert.equal(C.decode(b.stored()).notes[0].text,'Original');
  b.get('import-file').files=[{size:10,text:async()=>C.encode(C.empty())}];
  await b.event('import-file','change');
  assert.equal(b.get('notes-error').hidden,true);
  assert.equal(C.decode(b.stored()).notes.length,0);
});

test('failed import retains previous notebook and pending text',async()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-text').value='Original';b.event('note-text','input');b.tick();
  b.failWrites(true);
  b.get('import-file').files=[{size:10,text:async()=>C.encode(C.empty())}];
  await b.event('import-file','change');
  assert.match(b.get('notes-error').textContent,/carnet précédent conservé/);
  assert.equal(C.decode(b.stored()).notes[0].text,'Original');
  b.failWrites(false);b.event('save-now','click');
  assert.equal(C.decode(b.stored()).notes[0].text,'Original');
});


test('ADR-005: mode tabs use roving keyboard focus, arrows, Home and End',()=>{
  const b=browser();b.event('toolbar-new','click');
  assert.equal(b.get('tab-text').tabIndex,0);
  assert.equal(b.get('tab-sketch').tabIndex,-1);
  b.event('tab-text','keydown',{key:'ArrowRight'});
  assert.equal(b.get('tab-text').attrs['aria-selected'],'false');
  assert.equal(b.get('tab-sketch').attrs['aria-selected'],'true');
  assert.equal(b.get('tab-sketch').tabIndex,0);
  assert.equal(b.active(),b.get('tab-sketch'));
  b.event('tab-sketch','keydown',{key:'Home'});
  assert.equal(b.get('tab-text').attrs['aria-selected'],'true');
  assert.equal(b.active(),b.get('tab-text'));
  b.event('tab-text','keydown',{key:'End'});
  assert.equal(b.get('tab-sketch').attrs['aria-selected'],'true');
  b.event('tab-sketch','keydown',{key:'ArrowLeft'});
  assert.equal(b.get('tab-text').attrs['aria-selected'],'true');
});

test('ADR-005: invalid title error clears on repair, empty title normalizes on blur',()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-title').value='   ';b.event('note-title','input');
  assert.match(b.get('notes-error').textContent,/Titre requis/);
  b.get('note-title').value='Carnet';b.event('note-title','input');
  assert.equal(b.get('notes-error').hidden,true);
  b.get('note-title').value='';b.event('note-title','input');
  b.event('note-title','blur');
  assert.equal(b.get('note-title').value,'Sans titre');
  b.tick();
  assert.equal(C.decode(b.stored()).notes[0].title,'Sans titre');
});

test('two tabs refuse stale writes and export a rescue JSON without overwriting another tab',async()=>{
  const note=C.blank('note_001','2026-10-15T08:00:00.000Z');
  const sharedStorage={value:C.encode(C.upsert(C.empty(),note))};
  const first=browser({sharedStorage}),second=browser({sharedStorage});
  first.get('note-text').value='Version de A';
  first.event('note-text','input');first.tick();
  assert.equal(C.decode(sharedStorage.value).notes[0].text,'Version de A');
  second.get('note-text').value='Version de B';
  second.event('note-text','input');second.tick();
  assert.equal(C.decode(sharedStorage.value).notes[0].text,'Version de A');
  assert.equal(second.get('note-text').value,'Version de B');
  assert.equal(second.get('save-status').textContent,'Non enregistré');
  assert.match(second.get('notes-error').textContent,/autre onglet/);
  second.event('save-now','click');
  assert.equal(C.decode(sharedStorage.value).notes[0].text,'Version de A');
  second.event('export-json','click');
  assert.deepEqual(second.downloads,['PMKB-Notes-sauvegarde.json']);
  assert.equal(C.decode(await second.blobs[0].text()).notes[0].text,'Version de B');
  assert.equal(second.get('notes-error').hidden,false);
  const reopened=browser({sharedStorage});
  assert.equal(reopened.get('note-text').value,'Version de A');
});

test('storage event warns immediately, cancels pending save and ignores unrelated keys',async()=>{
  const note=C.blank('note_001','2026-10-15T08:00:00.000Z');
  const sharedStorage={value:C.encode(C.upsert(C.empty(),note))};
  const first=browser({sharedStorage}),second=browser({sharedStorage});
  second.get('note-text').value='B en mémoire';
  second.event('note-text','input');
  first.get('note-text').value='A enregistré';
  first.event('note-text','input');first.tick();
  const written=sharedStorage.value;
  second.signalStorage(written,'unrelated-key');
  assert.equal(second.get('save-status').textContent,'En attente…');
  second.signalStorage(written);
  assert.equal(second.get('save-status').textContent,'Non enregistré');
  assert.match(second.get('notes-error').textContent,/JSON/);
  second.tick();
  assert.equal(sharedStorage.value,written);
  assert.equal(second.get('note-text').value,'B en mémoire');
  second.event('export-json','click');
  assert.equal(C.decode(await second.blobs[0].text()).notes[0].text,'B en mémoire');
});

test('deleted external key cannot be overwritten; empty stored JSON is corrupt',()=>{
  const note=C.blank('note_001','2026-10-15T08:00:00.000Z');
  const sharedStorage={value:C.encode(C.upsert(C.empty(),note))};
  const tab=browser({sharedStorage});
  sharedStorage.value=null;
  tab.get('note-text').value='Texte de secours';
  tab.event('note-text','input');tab.tick();
  assert.equal(sharedStorage.value,null);
  assert.match(tab.get('notes-error').textContent,/autre onglet/);
  const corrupt=browser({initial:''});
  assert.equal(corrupt.get('save-status').textContent,'Non enregistré');
  assert.equal(corrupt.get('notes-error').hidden,false);
  corrupt.event('save-now','click');
  assert.equal(corrupt.stored(),'');
});

test('Ctrl+Z restores deletion and Ctrl+Y deletes again with persisted history',()=>{
  const b=browser();
  b.event('toolbar-new','click');
  b.get('note-title').value='Recette';b.event('note-title','input');
  b.get('note-text').value='Important';b.event('note-text','input');b.tick();
  const original=C.decode(b.stored()).notes[0];
  b.event('delete-note','click');b.tick();
  assert.equal(C.decode(b.stored()).notes.length,0);
  assert.equal(b.get('undo-action').disabled,false);
  assert.equal(b.key('z',{ctrlKey:true}).defaultPrevented,true);
  assert.equal(C.decode(b.stored()).notes[0].id,original.id);
  assert.equal(C.decode(b.stored()).notes[0].text,'Important');
  assert.equal(b.get('note-title').value,'Recette');
  b.key('y',{ctrlKey:true});b.tick();
  assert.equal(C.decode(b.stored()).notes.length,0);
  b.event('undo-action','click');
  assert.equal(C.decode(b.stored()).notes[0].title,'Recette');
});

test('duplicate creates independent ID and editable copy; undo/redo preserves latest copy text',()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-title').value='Source';b.event('note-title','input');
  b.get('note-text').value='À préserver';b.event('note-text','input');b.tick();
  const original=C.decode(b.stored()).notes[0];
  b.event('duplicate-note','click');
  let notes=C.decode(b.stored()).notes;
  assert.equal(notes.length,2);
  const copy=notes.find(n=>n.id!==original.id);
  assert.match(copy.title,/^Copie de Source/);
  assert.equal(copy.text,original.text);
  b.get('note-text').value='Copie modifiée';
  b.event('note-text','input');b.tick();
  const e=b.key('z',{metaKey:true});assert.equal(e.defaultPrevented,true);
  notes=C.decode(b.stored()).notes;assert.equal(notes.length,1);
  assert.equal(notes[0].id,original.id);
  assert.equal(notes[0].text,'À préserver');
  b.key('z',{metaKey:true,shiftKey:true});
  notes=C.decode(b.stored()).notes;assert.equal(notes.length,2);
  assert.equal(notes.find(n=>n.id===copy.id).text,'Copie modifiée');
});

test('native typing shortcuts are untouched and a new edit invalidates redo',()=>{
  const b=browser();b.event('toolbar-new','click');
  const title=b.get('note-title'),txt=b.get('note-text');
  assert.notEqual(b.key('z',{ctrlKey:true,target:txt}).defaultPrevented,true);
  assert.notEqual(b.key('y',{ctrlKey:true,target:title}).defaultPrevented,true);
  b.event('delete-note','click');b.event('undo-action','click');
  b.get('note-text').value='Nouveau texte';b.event('note-text','input');b.tick();
  assert.equal(b.get('redo-action').disabled,true);
  assert.notEqual(b.key('y',{ctrlKey:true}).defaultPrevented,true);
  assert.equal(C.decode(b.stored()).notes[0].text,'Nouveau texte');
});

test('new note may be undone then redone without losing text entered before undo',()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('note-text').value='Contenu avant annulation';
  b.event('note-text','input');b.tick();
  b.event('undo-action','click');b.tick();
  assert.equal(C.decode(b.stored()).notes.length,0);
  b.event('redo-action','click');b.tick();
  assert.equal(C.decode(b.stored()).notes[0].text,'Contenu avant annulation');
});

test('draw stroke, undo, redo and clear sketch preserve strokes',()=>{
  const b=browser();b.event('toolbar-new','click');
  b.event('tab-sketch','click');
  b.event('sketch','pointerdown',{button:0,pointerType:'mouse',
    pointerId:1,clientX:20,clientY:30});
  b.event('sketch','pointermove',{pointerId:1,clientX:34,clientY:40});
  b.event('sketch','pointerup',{pointerId:1});
  b.tick(); // Sketch strokes use the same 350 ms autosave as text.
  let strokes=C.decode(b.stored()).notes[0].strokes;
  assert.equal(strokes.length,1);
  assert.deepEqual(strokes[0].points,[[20,30],[34,40]]);
  b.event('undo','click');
  assert.equal(C.decode(b.stored()).notes[0].strokes.length,0);
  b.event('redo','click');
  assert.equal(C.decode(b.stored()).notes[0].strokes.length,1);
  b.event('clear-sketch','click');
  b.tick(); // Wait for deferred persistence before checking the stored carnet.
  assert.equal(C.decode(b.stored()).notes[0].strokes.length,0);
  b.key('z',{ctrlKey:true});
  assert.equal(C.decode(b.stored()).notes[0].strokes.length,1);
  b.key('y',{ctrlKey:true});
  assert.equal(C.decode(b.stored()).notes[0].strokes.length,0);
});

test('replaced notebook discards undo history; conflict guard still blocks writes',async()=>{
  const b=browser();b.event('toolbar-new','click');
  b.get('import-file').files=[{size:10,text:async()=>C.encode(C.empty())}];
  await b.event('import-file','change');
  assert.equal(b.get('undo-action').disabled,true);
  assert.equal(b.get('redo-action').disabled,true);
  assert.equal(C.decode(b.stored()).notes.length,0);
  const note=C.blank('note_001','2026-10-15T08:00:00.000Z');
  const shared={value:C.encode(C.upsert(C.empty(),note))};
  const first=browser({sharedStorage:shared}),second=browser({sharedStorage:shared});
  first.event('delete-note','click');first.tick();
  second.event('delete-note','click');second.tick();
  assert.match(second.get('notes-error').textContent,/autre onglet/);
  second.event('undo-action','click');
  second.event('redo-action','click');second.tick();
  assert.equal(C.decode(shared.value).notes.length,0);
  assert.match(second.get('notes-error').textContent,/autre onglet/);
});
