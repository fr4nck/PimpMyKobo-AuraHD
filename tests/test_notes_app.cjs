/* Exercise the real browser adapter with isolated DOM/storage/timer fixtures. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const C = require('../experimental/notes-v01/notes-core.js');
const app = path.join(__dirname, '../experimental/notes-v01');

function browser({readError=false, initial=null}={}) {
  const elements = new Map(), timers = new Map(), downloads = [];
  let serial=0, stored=initial, writeError=false;
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
      remove(){}, getContext(){return {fillRect(){},beginPath(){},arc(){},fill(){},moveTo(){},lineTo(){},stroke(){}}}
    };
  }
  const html=fs.readFileSync(path.join(app,'index.html'),'utf8');
  for(const match of html.matchAll(/<[^>]+id="([^"]+)"[^>]*>/g)) {
    const item=element(match[1]); item.hidden=/\bhidden\b/.test(match[0]); elements.set(item.id,item);
  }
  const document={activeElement:null, body:element(), fonts:{add(){}},
    getElementById:id=>elements.get(id), createElement:()=>element(),
    querySelectorAll:()=>[], addEventListener(){}};
  const window={PMKBNotesCore:C, confirm:()=>true, addEventListener(){},
    localStorage:{getItem(){if(readError)throw Error('blocked');return stored;},
      setItem(key,value){if(writeError)throw Error('quota');stored=value;}}};
  vm.runInNewContext(fs.readFileSync(path.join(app,'notes-app.js'),'utf8'),{
    window,document,Blob,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    setTimeout(callback){timers.set(++serial,callback);return serial;},
    clearTimeout(id){timers.delete(id);},console
  });
  return {get:id=>elements.get(id), downloads, stored:()=>stored,
    failWrites(value){writeError=value;},
    event(id,name){const item=elements.get(id);return item.listeners[name]({target:item});},
    tick(){const jobs=[...timers.values()];timers.clear();for(const job of jobs)job();}};
}

test('empty, pending and saved states remain compact; success has no error',()=>{
  const b=browser();
  assert.equal(b.get('save-status').textContent,'Carnet vide');
  assert.equal(b.get('notes-error').hidden,true);
  assert.equal(b.get('backup-result').hidden,true);
  b.event('toolbar-new','click');
  assert.equal(b.get('save-status').textContent,'Enregistré localement');
  b.get('note-text').value='Texte conservé';b.event('note-text','input');
  assert.equal(b.get('save-status').textContent,'En attente…');
  b.tick();
  assert.equal(C.decode(b.stored()).notes[0].text,'Texte conservé');
  assert.equal(b.get('notes-error').hidden,true);
});

test('write failure stays visible through JSON export; successful retry clears it',()=>{
  const b=browser();b.event('toolbar-new','click');b.failWrites(true);
  b.get('note-text').value='À sauvegarder';b.event('note-text','input');b.tick();
  assert.equal(b.get('save-status').textContent,'Non enregistré');
  assert.equal(b.get('notes-error').hidden,false);
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
