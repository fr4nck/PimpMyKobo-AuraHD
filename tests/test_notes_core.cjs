"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const N=require("../experimental/notes-v01/notes-core.js");
const T1="2026-10-13T10:00:00.000Z";
const T2="2026-10-13T10:30:00.000Z";
const original=()=>N.blank("note_001",T1);

test("empty notebook with strict portable format",()=>{
  assert.deepEqual(N.empty(),{format:"pmkb-notes-v1",notes:[]});
  assert.deepEqual(N.decode(N.encode(N.empty())),N.empty());
  assert.equal(N.MAX_NOTES,100);
  assert.equal(N.PAGE.width,900);
  assert.equal(N.PAGE.height,600);
  assert.deepEqual(N.BRUSHES,[2,5,11]);
});
test("create text notes, UTF-8, edit without mutating prior book",()=>{
  const blank=original();
  const first=N.upsert(N.empty(),blank);
  const updated={...blank,title:"Été & poésie 🖊️",text:"Une idée.\nEt une deuxième.",updated:T2};
  const next=N.upsert(first,updated);
  assert.equal(first.notes[0].title,"Sans titre");
  assert.equal(next.notes[0].title,"Été & poésie 🖊️");
  assert.equal(next.notes[0].text,"Une idée.\nEt une deuxième.");
  assert.deepEqual(N.decode(N.encode(next)),next);
  assert.notEqual(next.notes[0],updated);
});
test("search title and content, case-insensitive, ordered by updated timestamp",()=>{
  const a={...original(),id:"note_002",title:"Courses",text:"pain",updated:T2};
  const b={...original(),id:"note_003",title:"Recettes",text:"PAIN et huile"};
  let book=N.upsert(N.empty(),b);
  book=N.upsert(book,a);
  assert.deepEqual(N.sorted(book).map(n=>n.id),["note_002","note_003"]);
  assert.deepEqual(N.sorted(book,"pain").map(n=>n.id),["note_002","note_003"]);
  assert.deepEqual(N.sorted(book,"  ReCeTtEs ").map(n=>n.id),["note_003"]);
  assert.deepEqual(N.sorted(book,"introuvable"),[]);
});
test("delete only selected note, other notes unchanged",()=>{
  let book=N.upsert(N.empty(),original());
  book=N.upsert(book,{...original(),id:"note_002"});
  const result=N.remove(book,"note_001");
  assert.equal(result.notes.length,1);
  assert.equal(result.notes[0].id,"note_002");
  assert.equal(book.notes.length,2);
  assert.deepEqual(N.remove(result,"missing"),result);
});
test("brush stroke point data, undo, JSON roundtrip",()=>{
  const path=N.stroke("pen",5,[[10,15],[20,50],[30,55]]);
  let n=N.addStroke(original(),path,T2);
  assert.equal(n.strokes.length,1);
  assert.equal(n.strokes[0].tool,"pen");
  assert.equal(original().strokes.length,0);
  const eraser=N.stroke("eraser",11,[[24,25]]);
  n=N.addStroke(n,eraser,T2);
  const book=N.upsert(N.empty(),n);
  assert.deepEqual(N.decode(N.encode(book)),book);
  const reverted=N.dropStroke(n,T2);
  assert.equal(reverted.strokes.length,1);
  assert.equal(n.strokes.length,2);
  assert.deepEqual(N.dropStroke(original(),T2),original());
});
test("coordinate clamp and strict invalid points",()=>{
  assert.deepEqual(N.point(-10,900),[0,600]);
  assert.deepEqual(N.point(12.7,45.2),[13,45]);
  assert.throws(()=>N.point(NaN,4),/Coordonnées/);
  assert.throws(()=>N.point(Infinity,0),/Coordonnées/);
  for(const bad of [
    ["pen",1,[[1,1]]],
    ["paint",5,[[1,1]]],
    ["pen",5,[]],
    ["pen",5,[[1.5,0]]],
    ["eraser",11,[[-1,0]]],
    ["pen",2,[[901,20]]],
    ["pen",5,[[0,601]]],
    ["pen",5,[[NaN,0]]],
    ["pen",5,[["1",0]]]
  ])assert.throws(()=>N.stroke(...bad));
});
test("malformed and malicious imported notebook rejected",()=>{
  for(const value of [
    {},[],{format:"other",notes:[]},
    {format:N.FORMAT,notes:"bad"},
    {format:N.FORMAT,notes:[{id:"evil",title:"<script>"}]},
    {format:N.FORMAT,notes:[original(),original()]},
    {format:N.FORMAT,notes:[{...original(),text:5}]},
    {format:N.FORMAT,notes:[{...original(),strokes:[{tool:"pen",width:5,points:[[0,0],[1000,1]]}]}]}
  ])assert.throws(()=>N.validate(value));
  assert.throws(()=>N.decode("not JSON"),/JSON/);
  assert.throws(()=>N.decode('{"format":"unexpected","notes":[]}'),/Format/);
  assert.throws(()=>N.decode("x".repeat(N.MAX_IMPORT_BYTES+1)),/volumineux/);
});
test("limits on titles, body, notes, strokes and points",()=>{
  assert.throws(()=>N.blank("!",T1));
  assert.throws(()=>N.blank("note_001","tomorrow"));
  assert.throws(()=>N.note({...original(),title:"x".repeat(N.MAX_TITLE+1)}));
  assert.throws(()=>N.note({...original(),text:"x".repeat(N.MAX_TEXT+1)}));
  assert.throws(()=>N.stroke("pen",2,Array(N.MAX_POINTS+1).fill([1,1])));
  let book=N.empty();
  for(let i=0;i<N.MAX_NOTES;i++){
    book=N.upsert(book,N.blank("note_"+String(i).padStart(3,"0"),T1));
  }
  assert.throws(()=>N.upsert(book,N.blank("note_extra",T1)),/plein/);
  assert.equal(N.upsert(book,{...book.notes[0],title:"Modifié"}).notes.length,N.MAX_NOTES);
  const full={...original(),strokes:Array(N.MAX_STROKES).fill(N.stroke("pen",2,[[1,1]]))};
  assert.throws(()=>N.addStroke(full,N.stroke("pen",2,[[1,1]]),T1),/Maximum/);
});
test("filename export strips paths and uses allowed extensions",()=>{
  assert.equal(N.safeFilename("../../école/notes ✏","txt"),"ecolenotes.txt");
  assert.equal(N.safeFilename("   ","png"),"note.png");
  assert.equal(N.safeFilename("Ma note","exe"),"Ma-note.txt");
});
test("validating a notebook never retains imported mutable objects",()=>{
  const source={format:N.FORMAT,notes:[original()]};
  const parsed=N.validate(source);
  source.notes[0].title="changed";
  assert.equal(parsed.notes[0].title,"Sans titre");
  parsed.notes[0].title="edited";
  assert.equal(source.notes[0].title,"changed");
});

test("V0.2 typography defaults preserve preexisting V0.1 JSON",()=>{
  const note=N.blank("note_old",T1);
  delete note.typography; // exported V0.1 had no typography key
  const legacy=JSON.stringify({format:N.FORMAT,notes:[note]});
  const restored=N.decode(legacy);
  assert.deepEqual(restored.notes[0].typography,{font:"mono",size:17,lineHeight:1.6});
  assert.equal(restored.notes[0].text,"");
  assert.deepEqual(N.decode(N.encode(restored)),restored);
  assert.deepEqual(N.FONTS,["mono","sans","serif","handwriting"]);
});

test("per-note font, font size and line spacing round trip without affecting strokes",()=>{
  const n=N.blank("note_font",T1);
  const customized={...n,title:"Typographie",text:"école",typography:{font:"serif",size:24,lineHeight:1.8}};
  const book=N.upsert(N.empty(),customized);
  const copy=N.decode(N.encode(book));
  assert.deepEqual(copy.notes[0].typography,{font:"serif",size:24,lineHeight:1.8});
  assert.deepEqual(N.blank("note_new",T1).typography,N.DEFAULT_TYPE);
  assert.notStrictEqual(N.blank("note_new",T1).typography,N.DEFAULT_TYPE);
  assert.equal(customized.text,"école");
});

test("imported font references remain identifiers (never raw CSS or binary)",()=>{
  const id="import:123456789abc";
  assert.deepEqual(N.typography({font:id,size:17,lineHeight:1.4}),{
    font:id,size:17,lineHeight:1.4
  });
  const n={...N.blank("note_font",T1),typography:{font:id,size:20,lineHeight:1.6}};
  assert.deepEqual(N.decode(N.encode(N.upsert(N.empty(),n))).notes[0].typography,n.typography);
  for(const bad of [
    {font:"url(javascript:alert(1))",size:17,lineHeight:1.6},
    {font:"import:../../secret",size:17,lineHeight:1.6},
    {font:"import:1234",size:17,lineHeight:1.6},
    {font:"serif",size:7,lineHeight:1.6},
    {font:"serif",size:37,lineHeight:1.6},
    {font:"serif",size:"20",lineHeight:1.6},
    {font:"mono",size:18,lineHeight:1.3},
    {font:"mono",size:18,lineHeight:NaN},
    {font:"mono",size:18,lineHeight:"1.6"},
    {font:"mono",size:18},
    null
  ]) assert.throws(()=>N.typography(bad));
});
