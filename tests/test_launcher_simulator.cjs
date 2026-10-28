// Host-only V0.4 model checks. Zero browser dependencies, no devices.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const m = require("../experimental/launcher-v0/simulator.js");

test("approved portrait ordering and safe hit zones", () => {
  assert.deepEqual(m.TILES.map(x=>x.id),[
    "books","apps","games","web","recipes","notes","store","settings"
  ]);
  for (let i=0;i<m.TILES.length;i++) {
    const a=m.TILES[i];
    assert.ok(a.x>=0 && a.y>=0 && a.x+a.w<=m.WIDTH && a.y+a.h<=m.HEIGHT);
    assert.ok(a.y+a.h<m.BAR.y,"tile never covers status bar");
    for (let j=0;j<i;j++) {
      const b=m.TILES[j];
      const intersects=a.x < b.x+b.w && b.x < a.x+a.w
        && a.y < b.y+b.h && b.y < a.y+a.h;
      assert.equal(intersects,false,"tiles must never overlap");
    }
  }
  assert.ok(m.BAR.x>=0 && m.BAR.y>=0
    && m.BAR.x+m.BAR.w<=m.WIDTH && m.BAR.y+m.BAR.h<=m.HEIGHT);
});

test("no invented telemetry; state updates are immutable and validated", () => {
  const empty=m.defaults();
  assert.equal(empty.battery,null);
  assert.equal(empty.wifi,"unknown");
  assert.equal(m.labelFor("battery",empty),"BAT --");
  assert.equal(m.labelFor("wifi",empty),"WIFI ?");
  const next=m.withSample(empty,{battery:87,charging:true,wifi:"off",frontlight:25,contrast:"normal"});
  assert.equal(m.labelFor("battery",next),"BAT 87%+");
  assert.equal(m.labelFor("frontlight",next),"LED 25%");
  assert.equal(m.labelFor("wifi",next),"WIFI OFF");
  assert.equal(empty.battery,null);
  assert.equal(empty.wifi,"unknown");
  assert.notEqual(empty,next);
  for (const invalid of [-1,101,1.5,NaN,Infinity,"87"]) {
    assert.throws(()=>m.withSample(empty,{battery:invalid}));
  }
  assert.throws(()=>m.withSample(empty,{wifi:"enabled"}));
  assert.throws(()=>m.withSample(empty,{charging:"yes"}));
  assert.throws(()=>m.withSample(empty,{voltage:4000}));
  assert.equal(m.withSample(next,{battery:null}).battery,null);
});

test("only Books has an inert intent, all other apps unavailable",()=>{
  assert.deepEqual(m.tileAction("books"),{kind:"intent",name:"open_reader",id:"books"});
  for (const x of m.TILES.slice(1)) {
    assert.deepEqual(m.tileAction(x.id),{kind:"unavailable",id:x.id});
  }
  assert.deepEqual(m.tileAction("shell"),{kind:"ignored"});
});

test("seven quick actions cannot operate any hardware",()=>{
  assert.deepEqual(m.CONTROLS,[
    "battery","wifi","frontlight","contrast","refresh","sleep","settings"
  ]);
  for(const id of m.CONTROLS) {
    assert.deepEqual(m.quickAction(id),{kind:"quick_request",id:id});
  }
  assert.deepEqual(m.quickAction("reboot"),{kind:"ignored"});
});

test("keyboard navigation stays in approved 2x4 portrait grid",()=>{
  assert.equal(m.selectionIndex(0,"ArrowRight"),1);
  assert.equal(m.selectionIndex(1,"ArrowRight"),1);
  assert.equal(m.selectionIndex(1,"ArrowDown"),3);
  assert.equal(m.selectionIndex(4,"ArrowDown"),6);
  assert.equal(m.selectionIndex(6,"ArrowDown"),6);
  assert.equal(m.selectionIndex(5,"ArrowLeft"),4);
  assert.equal(m.selectionIndex(0,"End"),0);
});

test("dock favorites are configurable but cannot execute unknown apps", () => {
  assert.deepEqual(m.DEFAULT_DOCK,["books","notes","recipes","web"]);
  assert.equal(m.MAX_DOCK,5);
  const custom=m.dockChoice(["books","games","settings"]);
  assert.deepEqual(custom,["books","games","settings"]);
  custom.push("store");
  assert.equal(m.DEFAULT_DOCK.length,4,"original dock untouched");
  for (const ids of [[],["books","books"],["books","shell"],["books","notes","games","web","apps","store"]]) {
    assert.throws(()=>m.dockChoice(ids));
  }
  assert.throws(()=>m.dockChoice("books"));
  assert.deepEqual(m.tileAction(m.DEFAULT_DOCK[0]),{kind:"intent",name:"open_reader",id:"books"});
  for(const id of m.DEFAULT_DOCK.slice(1)) {
    assert.equal(m.tileAction(id).kind,"unavailable");
  }
});

test("every tile has explicit light idle and dark selected state without editing art",()=>{
  const darkInApprovedImage=["books","web"];
  for(const tile of m.TILES) {
    assert.equal(m.tileTone(tile.id,false),"light");
    assert.equal(m.tileTone(tile.id,true),"dark");
    assert.equal(m.needsInversion(tile.id,false),darkInApprovedImage.includes(tile.id));
    assert.equal(m.needsInversion(tile.id,true),!darkInApprovedImage.includes(tile.id));
  }
  assert.equal(m.tileTone("invalid",true),null);
  assert.equal(m.needsInversion("invalid",true),false);
});
