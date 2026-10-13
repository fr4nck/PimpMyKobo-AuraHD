/* PMKB V0.6 — host-only simulated launcher.
 * No hardware/network/filesystem access, no image generation or image modification.
 * Entire tiles are click targets. Only their printed TITLE bands may invert.
 */
(function(root) {
  "use strict";
  const WIDTH=1080, HEIGHT=1440;
  const PNG="assets/v02/optimise/PMKB-V0.2-16gris.png";
  const TILES=Object.freeze([
    {id:"books",label:"Livres",enabled:true,x:59,y:70,w:475,h:315,bandY:315,bandH:65},
    {id:"apps",label:"Applications",enabled:false,x:543,y:70,w:479,h:315,bandY:315,bandH:65},
    {id:"games",label:"Jeux",enabled:false,x:59,y:396,w:475,h:310,bandY:635,bandH:66},
    {id:"web",label:"Web",enabled:false,x:543,y:396,w:479,h:310,bandY:635,bandH:66},
    {id:"recipes",label:"Recettes",enabled:false,x:59,y:717,w:475,h:291,bandY:939,bandH:65},
    {id:"notes",label:"Notes",enabled:false,x:543,y:717,w:479,h:291,bandY:939,bandH:65},
    {id:"store",label:"Boutique",enabled:false,x:59,y:1028,w:475,h:283,bandY:1247,bandH:61},
    {id:"settings",label:"Réglages",enabled:false,x:543,y:1028,w:479,h:283,bandY:1247,bandH:61}
  ]);
  // Only the six *existing* pictograms in the approved footer, in image order.
  const CONTROLS=Object.freeze(["wifi","battery","frontlight","contrast","refresh","sleep"]);
  const BAR=Object.freeze({x:58,y:1325,w:965,h:66});
  const ZONES=Object.freeze([
    {id:"wifi",x:0,w:201}, {id:"battery",x:201,w:149},
    {id:"frontlight",x:350,w:219}, {id:"contrast",x:569,w:205},
    {id:"refresh",x:774,w:101}, {id:"sleep",x:875,w:90}
  ]);
  const CONTROL_NAMES=Object.freeze({
    wifi:"Wi-Fi",battery:"Batterie",frontlight:"Éclairage",contrast:"Contraste",
    refresh:"Rafraîchir",sleep:"Veille"
  });

  function defaults() {
    return {battery:null,charging:null,wifi:"unknown",frontlight:null,contrast:"unknown"};
  }
  function percent(v) {return Number.isInteger(v) && v>=0 && v<=100;}
  function withSample(state,sample) {
    if (!state || !sample || typeof sample!=="object" || Array.isArray(sample)) {
      throw new Error("Invalid simulated telemetry");
    }
    const result=Object.assign({},state);
    for (const [key,value] of Object.entries(sample)) {
      if (key==="battery" || key==="frontlight") {
        if (value!==null && !percent(value)) throw new Error("Invalid "+key);
      } else if (key==="charging") {
        if (value!==null && typeof value!=="boolean") throw new Error("Invalid charging");
      } else if (key==="wifi") {
        if (!["unknown","off","connecting","connected"].includes(value)) throw new Error("Invalid wifi");
      } else if (key==="contrast") {
        if (!["unknown","normal","high","inverse"].includes(value)) throw new Error("Invalid contrast");
      } else {
        throw new Error("Unsupported telemetry key: "+key);
      }
      result[key]=value;
    }
    return result;
  }
  function labelFor(id,sample) {
    const s=sample || defaults();
    if(id==="battery") return s.battery==null ? "BAT --"
      : "BAT "+s.battery+"%"+(s.charging?"+":"");
    if(id==="wifi") return "WIFI "+({unknown:"?",off:"OFF",connecting:"...",connected:"OK"}[s.wifi]||"?");
    if(id==="frontlight") return s.frontlight==null ? "LED --" : "LED "+s.frontlight+"%";
    if(id==="contrast") return "CTR "+({unknown:"?",normal:"NORM",high:"HAUT",inverse:"INV"}[s.contrast]||"?");
    return {refresh:"RAF",sleep:"VEILLE"}[id]||"?";
  }
  function tileAction(id) {
    const item=TILES.find(t=>t.id===id);
    if(!item) return {kind:"ignored"};
    return item.enabled
      ? {kind:"intent",name:"open_reader",id:"books"}
      : {kind:"unavailable",id:id};
  }
  function quickAction(id) {
    return CONTROLS.includes(id)?{kind:"quick_request",id:id}:{kind:"ignored"};
  }
  function tileAt(x,y) {
    if (!Number.isFinite(x)||!Number.isFinite(y)) return null;
    const tile=TILES.find(t=>x>=t.x&&x<t.x+t.w&&y>=t.y&&y<t.y+t.h);
    return tile?tile.id:null;
  }
  function labelBand(id) {
    const tile=TILES.find(t=>t.id===id);
    return tile?{x:tile.x+6,y:tile.bandY,w:tile.w-12,h:tile.bandH}:null;
  }
  // Physical bitmap: only Books' printed label is dark by default.
  // Inversion applies exclusively to the clipped label region, NEVER the art.
  function bandNeedsInversion(id,selected) {
    return id==="books" ? !selected : Boolean(selected);
  }
  // First tap selects, second tap produces an inert action (no real launch).
  // A tap anywhere in the photo or its label follows the same rule.
  function tapSelection(selected,id) {
    if (!TILES.some(t=>t.id===id)) return {selected,action:{kind:"ignored"}};
    if (selected!==id) return {selected:id,action:{kind:"selected",id}};
    return {selected:id,action:tileAction(id)};
  }
  function selectionIndex(index,key) {
    const delta={ArrowLeft:-1,ArrowRight:1,ArrowUp:-2,ArrowDown:2}[key];
    if(!delta) return index;
    if(index<0) return 0;
    const next=index+delta;
    if(next<0||next>=TILES.length) return index;
    if ((key==="ArrowLeft"||key==="ArrowRight") &&
      Math.floor(index/2)!==Math.floor(next/2)) return index;
    return next;
  }
  function position(element,rect) {
    element.style.left=(rect.x/WIDTH*100)+"%";
    element.style.top=(rect.y/HEIGHT*100)+"%";
    element.style.width=(rect.w/WIDTH*100)+"%";
    element.style.height=(rect.h/HEIGHT*100)+"%";
  }
  // Composite only a strip of the same approved PNG; no encoded asset changes.
  function applyBandCrop(element,tile) {
    const b=labelBand(tile.id);
    element.style.left=(6/tile.w*100)+"%";
    element.style.top=((b.y-tile.y)/tile.h*100)+"%";
    element.style.width=(b.w/tile.w*100)+"%";
    element.style.height=(b.h/tile.h*100)+"%";
    element.style.backgroundImage='url("'+PNG+'")';
    element.style.backgroundSize=(WIDTH/b.w*100)+"% "+(HEIGHT/b.h*100)+"%";
    element.style.backgroundPosition=(b.x/(WIDTH-b.w)*100)+"% "+
      (b.y/(HEIGHT-b.h)*100)+"%";
  }
  function init() {
    const screen=document.getElementById("screen");
    if(!screen) return;
    const footer=document.getElementById("dynamic-status");
    const display=document.getElementById("event-log");
    const current=document.getElementById("selected-label");
    const selection=document.getElementById("scenario");
    const batteryInput=document.getElementById("battery-level");
    const lightInput=document.getElementById("frontlight-level");
    const demoBadge=document.getElementById("demo-badge");
    let state=defaults();
    let selected=null;  // Nothing is preselected; Books is white on first load.
    const tileButtons=[];

    function message(action) {
      if(action.kind==="selected") {
        const item=TILES.find(t=>t.id===action.id);
        display.textContent=(item?item.label:action.id)+" sélectionné. Second appui : confirmer.";
      } else if(action.kind==="intent") {
        display.textContent="Intention KOReader simulée, sans lancer de programme.";
      } else if(action.kind==="unavailable") {
        const item=TILES.find(t=>t.id===action.id);
        display.textContent=(item?item.label:action.id)+" : à venir.";
      } else if(action.kind==="quick_request") {
        display.textContent=CONTROL_NAMES[action.id]+" : commande simulée, aucune action matérielle.";
      }
    }
    function renderSelection() {
      tileButtons.forEach(function(button,i){
        const tile=TILES[i];
        const active=tile.id===selected;
        button.classList.toggle("selected",active);
        // Invert just the label crop; the photo above is the original bitmap.
        button.querySelector(".label-band").classList.toggle("inverted",bandNeedsInversion(tile.id,active));
        button.setAttribute("aria-pressed",active?"true":"false");
      });
      const item=TILES.find(t=>t.id===selected);
      current.textContent=item
        ? item.label+(item.enabled?" · KOReader (simulation)":" · à venir")
        : "Aucune";
    }
    function tapTile(id) {
      const result=tapSelection(selected,id);
      selected=result.selected;
      renderSelection();
      message(result.action);
    }
    for(const tile of TILES) {
      const button=document.createElement("button");
      button.type="button";
      button.className="tile-target";
      button.dataset.tile=tile.id;
      button.setAttribute("aria-label",tile.label+", vignette complète (premier appui : sélectionner)");
      button.setAttribute("aria-pressed","false");
      position(button,tile); // Entire photo + label are the clickable area.
      const band=document.createElement("span");
      band.className="label-band";
      band.setAttribute("aria-hidden","true");
      applyBandCrop(band,tile);
      button.appendChild(band);
      button.addEventListener("click",()=>tapTile(tile.id));
      screen.appendChild(button);
      tileButtons.push(button);
    }
    position(footer,BAR);
    for(const zone of ZONES) {
      const button=document.createElement("button");
      button.type="button";
      button.className="system-target";
      button.dataset.control=zone.id;
      button.title=CONTROL_NAMES[zone.id]+" (simulation)";
      button.setAttribute("aria-label",CONTROL_NAMES[zone.id]+" (simulation)");
      button.style.left=(zone.x/BAR.w*100)+"%";
      button.style.width=(zone.w/BAR.w*100)+"%";
      button.addEventListener("click",()=>message(quickAction(zone.id)));
      footer.appendChild(button);
    }
    // Replace ONLY the illustrative value text/meters, not the footer pictograms.
    const readouts=document.getElementById("status-readouts");
    function readout(id,rect) {
      const el=document.createElement("span");
      el.className="readout "+id;
      el.dataset.readout=id;
      position(el,rect);
      readouts.appendChild(el);
      return el;
    }
    const wifiText=readout("wifi",{x:138,y:1338,w:111,h:41});
    const batteryText=readout("battery",{x:335,y:1343,w:68,h:30});
    const frontlightMeter=readout("frontlight",{x:489,y:1344,w:121,h:29});
    const contrastMeter=readout("contrast",{x:710,y:1344,w:112,h:29});
    function renderTelemetry() {
      const wifiLabel={unknown:"?",off:"OFF",connecting:"...",connected:"OK"};
      wifiText.textContent="Wi-Fi\n"+wifiLabel[state.wifi];
      batteryText.textContent=state.battery==null?"--":state.battery+"%"+(state.charging?"+":"");
      function squares(count) {return "\u25A0".repeat(count)+"\u25A1".repeat(6-count);}
      const lit=state.frontlight==null?0:Math.ceil(state.frontlight/100*6);
      frontlightMeter.textContent=state.frontlight==null?"--":squares(lit);
      contrastMeter.textContent=state.contrast==="unknown"?"--":
        squares({normal:2,high:4,inverse:6}[state.contrast]);
      footer.querySelectorAll(".system-target").forEach(button=>{
        button.title=CONTROL_NAMES[button.dataset.control]+" : "+labelFor(button.dataset.control,state)+" (simulation)";
      });
    }
    const presets={
      unknown:defaults(),
      offline:{battery:74,charging:false,wifi:"off",frontlight:15,contrast:"normal"},
      connected:{battery:87,charging:false,wifi:"connected",frontlight:25,contrast:"normal"},
      charging:{battery:92,charging:true,wifi:"off",frontlight:10,contrast:"high"}
    };
    function choosePreset() {
      state=withSample(defaults(),presets[selection.value]||presets.unknown);
      batteryInput.value=state.battery==null?0:state.battery;
      lightInput.value=state.frontlight==null?0:state.frontlight;
      demoBadge.textContent=selection.options[selection.selectedIndex].text+" · fictif";
      renderTelemetry();
      display.textContent="Données de démonstration uniquement, aucun matériel interrogé.";
    }
    selection.addEventListener("change",choosePreset);
    batteryInput.addEventListener("input",()=>{
      state=withSample(state,{battery:Number(batteryInput.value)});renderTelemetry();
    });
    lightInput.addEventListener("input",()=>{
      state=withSample(state,{frontlight:Number(lightInput.value)});renderTelemetry();
    });
    screen.addEventListener("keydown",event=>{
      if (["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key)) {
        event.preventDefault();
        const idx=TILES.findIndex(t=>t.id===selected);
        const next=selectionIndex(idx,event.key);
        selected=TILES[next].id;
        renderSelection();message({kind:"selected",id:selected});
      } else if (event.key==="Enter" && event.target===screen) {
        event.preventDefault();
        tapTile(selected||"books");
      }
    });
    document.getElementById("activate").addEventListener("click",()=>tapTile(selected||"books"));
    document.getElementById("reset").addEventListener("click",()=>{
      selected=null;renderSelection();selection.value="unknown";choosePreset();
    });
    renderSelection();
    choosePreset();
  }
  const API={WIDTH,HEIGHT,PNG,TILES,CONTROLS,BAR,ZONES,defaults,withSample,labelFor,
    tileAction,quickAction,tileAt,labelBand,bandNeedsInversion,tapSelection,selectionIndex};
  if(typeof module!=="undefined"&&module.exports)module.exports=API;
  if(root&&root.document)root.addEventListener("DOMContentLoaded",init);
})(typeof window!=="undefined"?window:null);
