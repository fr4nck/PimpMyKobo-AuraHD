/* Exercise the real browser adapter with isolated DOM/storage/timer fixtures. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const C = require('../experimental/notes-v01/notes-core.js');
const app = path.join(__dirname, '../experimental/notes-v01');

function browser({readError=false, initial=null, confirmReply=true}={}) {
  const elements = new Map(), timers = new Map(), downloads = [];
  let serial=0, stored=initial, writeError=false, destination=null;
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
      getContext(){return {fillRect(){},beginPath(){},arc(){},fill(){},moveTo(){},lineTo(){},stroke(){}}}
    };
  }
  const html=fs.readFileSync(path.join(app,'index.html'),'utf8');
  for(const match of html.matchAll(/<[^>]+id="([^"]+)"[^>]*>/g)) {
    const item=element(match[1]); item.hidden=/\bhidden\b/.test(match[0]); elements.set(item.id,item);
  }
  const document={activeElement:null, body:element(), fonts:{add(){}},
    getElementById:id=>elements.get(id), createElement:()=>element(),
    querySelectorAll:()=>[], addEventListener(){}};
  const window={PMKBNotesCore:C, confirm:()=>confirmReply, addEventListener(){},
    location:{assign(url){destination=url;}},
    localStorage:{getItem(){if(readError)throw Error('blocked');return stored;},
      setItem(key,value){if(writeError)throw Error('quota');stored=value;}}};
  vm.runInNewContext(fs.readFileSync(path.join(app,'notes-app.js'),'utf8'),{
    window,document,Blob,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    setTimeout(callback){timers.set(++serial,callback);return serial;},
    clearTimeout(id){timers.delete(id);},console
  });
  return {get:id=>elements.get(id), downloads, stored:()=>stored, destination:()=>destination,
    failWrites(value){writeError=value;},
    event(id,name){const item=elements.get(id);return item.listeners[name]({target:item});},
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
