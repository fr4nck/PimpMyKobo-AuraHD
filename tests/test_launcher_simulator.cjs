// V0.6 host-only launcher behavior. Node built-in test runner; zero hardware.
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const m=require("../experimental/launcher-v0/simulator.js");

test("eight ordered tiles are entire touch targets, artwork AND label",()=>{
  assert.deepEqual(m.TILES.map(t=>t.id),[
    "books","apps","games","web","recipes","notes","store","settings"
  ]);
  for(let i=0;i<m.TILES.length;i++){
    const t=m.TILES[i], b=m.labelBand(t.id);
    assert.ok(t.x>=0&&t.y>=0&&t.x+t.w<=m.WIDTH&&t.y+t.h<=m.HEIGHT);
    assert.ok(t.y+t.h<m.BAR.y,"tile separate from system controls");
    assert.ok(b.x>=t.x&&b.x+b.w<=t.x+t.w,"ribbon within full button");
    assert.ok(b.y>t.y && b.y+b.h<=t.y+t.h,"ribbon under art, within button");
    assert.equal(m.tileAt(t.x+12,t.y+12),t.id,"photo region clickable");
    assert.equal(m.tileAt(b.x+12,b.y+12),t.id,"text band clickable");
    for(let j=0;j<i;j++){
      const u=m.TILES[j];
      assert.ok(t.x>=u.x+u.w || u.x>=t.x+t.w || t.y>=u.y+u.h || u.y>=t.y+t.h);
    }
  }
  assert.equal(m.tileAt(0,0),null);
  assert.equal(m.tileAt(NaN,400),null);
  assert.equal(m.tileAt(Infinity,400),null);
  assert.equal(m.labelBand("invalid"),null);
});

test("unselected labels white, selected labels dark, with no illustration filter",()=>{
  assert.equal(m.bandNeedsInversion("books",false),true,"original black Books ribbon whitened");
  assert.equal(m.bandNeedsInversion("books",true),false,"original black Books ribbon when selected");
  for(const tile of m.TILES.slice(1)){
    assert.equal(m.bandNeedsInversion(tile.id,false),false,"original light ribbon stays");
    assert.equal(m.bandNeedsInversion(tile.id,true),true,"only ribbon is inverted");
  }
});

test("first tap selects, second tap confirms, changing tiles deselects previous",()=>{
  let selected=null;
  const first=m.tapSelection(selected,"books");
  assert.deepEqual(first,{selected:"books",action:{kind:"selected",id:"books"}});
  selected=first.selected;
  assert.deepEqual(m.tapSelection(selected,"books"),{
    selected:"books",action:{kind:"intent",name:"open_reader",id:"books"}
  });
  const second=m.tapSelection(selected,"web");
  assert.equal(second.selected,"web");
  assert.deepEqual(second.action,{kind:"selected",id:"web"});
  assert.equal(m.bandNeedsInversion("books",false),true,"Books returns white");
  assert.deepEqual(m.tapSelection(second.selected,"web"),{
    selected:"web",action:{kind:"unavailable",id:"web"}
  });
  assert.deepEqual(m.tapSelection(null,"shell"),{selected:null,action:{kind:"ignored"}});
});

test("only the six ORIGINAL system pictograms are interactive",()=>{
  assert.deepEqual(m.CONTROLS,["wifi","battery","frontlight","contrast","refresh","sleep"]);
  assert.deepEqual(m.ZONES.map(x=>x.id),m.CONTROLS);
  let end=0;
  for(const z of m.ZONES){
    assert.equal(z.x,end,"no gaps/overlaps");
    assert.ok(z.w>0);
    assert.deepEqual(m.quickAction(z.id),{kind:"quick_request",id:z.id});
    end=z.x+z.w;
  }
  assert.equal(end,m.BAR.w);
  for(const id of ["books","notes","settings","dock"]){
    assert.deepEqual(m.quickAction(id),{kind:"ignored"});
  }
});

test("telemetry stays simulated, validated and immutable",()=>{
  const old=m.defaults();
  assert.deepEqual(old,{battery:null,charging:null,wifi:"unknown",frontlight:null,contrast:"unknown"});
  assert.equal(m.labelFor("battery",old),"BAT --");
  const next=m.withSample(old,{battery:87,charging:true,wifi:"off",frontlight:25,contrast:"normal"});
  assert.equal(m.labelFor("battery",next),"BAT 87%+");
  assert.equal(m.labelFor("wifi",next),"WIFI OFF");
  assert.equal(m.labelFor("frontlight",next),"LED 25%");
  assert.equal(old.battery,null,"original never mutated");
  for(const val of [-1,101,1.5,Infinity,NaN,"45"]){
    assert.throws(()=>m.withSample(old,{battery:val}));
  }
  assert.throws(()=>m.withSample(old,{wifi:"online"}));
  assert.throws(()=>m.withSample(old,{voltage:4000}));
});

test("keyboard navigation stays in approved 2x4 portrait grid",()=>{
  assert.equal(m.selectionIndex(-1,"ArrowDown"),0);
  assert.equal(m.selectionIndex(0,"ArrowRight"),1);
  assert.equal(m.selectionIndex(1,"ArrowRight"),1);
  assert.equal(m.selectionIndex(1,"ArrowDown"),3);
  assert.equal(m.selectionIndex(4,"ArrowDown"),6);
  assert.equal(m.selectionIndex(6,"ArrowDown"),6);
  assert.equal(m.selectionIndex(5,"ArrowLeft"),4);
  assert.equal(m.selectionIndex(0,"End"),0);
});

test("footer targets meet the provisional physical touch dimensions",()=>{
  assert.equal(m.AURA_HD_PPI,265);
  assert.deepEqual(m.PRINTED_BAR,{x:58,y:1325,w:965,h:66});
  assert.deepEqual(m.BAR,{x:58,y:1317,w:965,h:113});
  assert.ok(m.mmFromPixels((66-4)/2)<4,"former two-row dock was under 4 mm high");
  assert.ok(m.mmFromPixels(m.BAR.h)>=10);
  assert.ok(m.BAR.y>Math.max(...m.TILES.map(t=>t.y+t.h)),"no artwork obscured");
  assert.ok(m.BAR.y<=m.PRINTED_BAR.y);
  assert.ok(m.BAR.y+m.BAR.h>=m.PRINTED_BAR.y+m.PRINTED_BAR.h);
  assert.ok(m.BAR.y+m.BAR.h<=m.HEIGHT);
  const rects=m.systemHitRects();
  assert.deepEqual(rects.map(r=>r.id),m.CONTROLS);
  rects.forEach((r,i)=>{
    const z=m.ZONES[i];
    assert.equal(r.x,m.BAR.x+z.x);
    assert.equal(r.w,z.w);
    assert.equal(r.y,m.BAR.y);
    assert.equal(r.h,m.BAR.h);
    assert.ok(m.mmFromPixels(r.w)>=8,r.id+" width >= 8 mm");
    assert.ok(m.mmFromPixels(r.h)>=10,r.id+" height >= 10 mm");
    if(i>0) assert.equal(rects[i-1].x+rects[i-1].w,r.x);
  });
});

test("tile arrows do not steal keyboard input from system controls",()=>{
  for(const key of ["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"]) {
    assert.equal(m.tileKeyAction(key,"screen"),"navigate");
    assert.equal(m.tileKeyAction(key,"tile"),"navigate");
    assert.equal(m.tileKeyAction(key,"other"),null);
  }
  assert.equal(m.tileKeyAction("Enter","screen"),"activate");
  assert.equal(m.tileKeyAction("Enter","tile"),null);
  assert.equal(m.tileKeyAction("Enter","other"),null);
  assert.equal(m.tileKeyAction(" ","other"),null);
  assert.equal(m.tileKeyAction("Tab","tile"),null);
});

test("visible black/white focus and last-request cues do not invert artwork",()=>{
  const fs=require("node:fs"),path=require("node:path");
  const html=fs.readFileSync(path.join(__dirname,"../experimental/launcher-v0/simulator.html"),"utf8");
  assert.match(html,/\.tile-target:focus-visible \{ outline:4px dashed #111;/);
  assert.match(html,/\.system-target\.requested \{ outline:4px solid #111;/);
  assert.match(html,/\.readout \{[^}]*background:white; color:black;/);
  assert.match(html,/touch-action:manipulation;/);
  assert.doesNotMatch(html,/\.artwork\s*\{[^}]*filter:/);
});
