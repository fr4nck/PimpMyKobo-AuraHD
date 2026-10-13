/* PMKB V0.4 — host-only illustrated launcher simulation.
 * No network, device, framebuffer, process, storage or real application access.
 * The approved 16-gray image is loaded unchanged by simulator.html.
 */
(function (root) {
  "use strict";

  const WIDTH = 1080;
  const HEIGHT = 1440;
  const TILES = Object.freeze([
    {id:"books", label:"Livres", enabled:true,  x:59, y:70,   w:475, h:315},
    {id:"apps", label:"Applications", enabled:false, x:543, y:70,  w:479, h:315},
    {id:"games", label:"Jeux", enabled:false, x:59, y:396,  w:475, h:310},
    {id:"web", label:"Web", enabled:false, x:543, y:396, w:479, h:310},
    {id:"recipes", label:"Recettes", enabled:false, x:59, y:717, w:475, h:291},
    {id:"notes", label:"Notes", enabled:false, x:543, y:717, w:479, h:291},
    {id:"store", label:"Boutique", enabled:false, x:59, y:1028, w:475, h:283},
    {id:"settings", label:"Réglages", enabled:false, x:543, y:1028, w:479, h:283}
  ]);
  const CONTROLS = Object.freeze(["battery","wifi","frontlight","contrast","refresh","sleep","settings"]);
  const BAR = Object.freeze({x:58,y:1325,w:965,h:66});
  const CONTROL_NAMES = Object.freeze({
    battery:"Batterie", wifi:"Wi-Fi", frontlight:"Éclairage",
    contrast:"Contraste", refresh:"Rafraîchir", sleep:"Veille", settings:"Réglages"
  });

  function defaults() {
    return {battery:null, charging:null, wifi:"unknown", frontlight:null, contrast:"unknown"};
  }

  function integerPercent(value) {
    return Number.isInteger(value) && value >= 0 && value <= 100;
  }

  function withSample(state, sample) {
    if (!state || !sample || typeof sample !== "object" || Array.isArray(sample)) {
      throw new Error("Invalid simulated telemetry");
    }
    const result = Object.assign({}, state);
    for (const [key,value] of Object.entries(sample)) {
      if (key === "battery" || key === "frontlight") {
        if (value !== null && !integerPercent(value)) throw new Error("Invalid " + key);
      } else if (key === "charging") {
        if (value !== null && typeof value !== "boolean") throw new Error("Invalid charging");
      } else if (key === "wifi") {
        if (!["unknown","off","connecting","connected"].includes(value)) {
          throw new Error("Invalid wifi");
        }
      } else if (key === "contrast") {
        if (!["unknown","normal","high","inverse"].includes(value)) {
          throw new Error("Invalid contrast");
        }
      } else {
        throw new Error("Unexpected telemetry key " + key);
      }
      result[key] = value;
    }
    return result;
  }

  function labelFor(id, sample) {
    const s = sample || defaults();
    if (id === "battery") {
      return s.battery === null || s.battery === undefined
        ? "BAT --" : "BAT " + s.battery + "%" + (s.charging ? "+" : "");
    }
    if (id === "wifi") {
      const states = {unknown:"?",off:"OFF",connecting:"...",connected:"OK"};
      return "WIFI " + (states[s.wifi] || "?");
    }
    if (id === "frontlight") {
      return s.frontlight === null || s.frontlight === undefined
        ? "LED --" : "LED " + s.frontlight + "%";
    }
    if (id === "contrast") {
      const states = {unknown:"?",normal:"NORM",high:"HAUT",inverse:"INV"};
      return "CTR " + (states[s.contrast] || "?");
    }
    return {refresh:"RAF",sleep:"VEILLE",settings:"REG"}[id] || "?";
  }

  function tileAction(id) {
    const item = TILES.find(function (tile) { return tile.id === id; });
    if (!item) return {kind:"ignored"};
    return item.enabled
      ? {kind:"intent",name:"open_reader",id:"books"}
      : {kind:"unavailable",id:item.id};
  }

  function quickAction(id) {
    return CONTROLS.includes(id) ? {kind:"quick_request",id:id} : {kind:"ignored"};
  }

  function selectionIndex(index, key) {
    const directions = {ArrowLeft:-1,ArrowRight:1,ArrowUp:-2,ArrowDown:2};
    const shift = directions[key];
    if (!shift || !Number.isInteger(index) || index < 0 || index >= TILES.length) return index;
    const next = index + shift;
    if (next < 0 || next >= TILES.length) return index;
    if ((key === "ArrowLeft" || key === "ArrowRight")
        && Math.floor(next / 2) !== Math.floor(index / 2)) return index;
    return next;
  }

  function position(element, rect) {
    element.style.left = (rect.x / WIDTH * 100) + "%";
    element.style.top = (rect.y / HEIGHT * 100) + "%";
    element.style.width = (rect.w / WIDTH * 100) + "%";
    element.style.height = (rect.h / HEIGHT * 100) + "%";
  }

  function init() {
    const stage = document.getElementById("screen");
    if (!stage) return;
    const statusBar = document.getElementById("dynamic-status");
    const display = document.getElementById("event-log");
    const title = document.getElementById("selected-label");
    const selection = document.getElementById("scenario");
    const batteryInput = document.getElementById("battery-level");
    const frontlightInput = document.getElementById("frontlight-level");
    const demoBadge = document.getElementById("demo-badge");
    let state = defaults();
    let focused = 0;
    const tileButtons = [];

    function announce(action) {
      if (action.kind === "intent") {
        display.textContent = "Intention simulée : ouvrir KOReader (aucun lancement).";
      } else if (action.kind === "unavailable") {
        const item = TILES.find(function (x) { return x.id === action.id; });
        display.textContent = (item ? item.label : action.id) + " : à venir.";
      } else if (action.kind === "quick_request") {
        display.textContent = CONTROL_NAMES[action.id] + " : demande simulée, aucune action matérielle.";
      }
    }
    function focusTile(index) {
      focused = index;
      tileButtons.forEach(function (button, i) {
        button.classList.toggle("selected", i === focused);
        button.setAttribute("aria-pressed", i === focused ? "true" : "false");
      });
      title.textContent = TILES[focused].label + (TILES[focused].enabled ? " · KOReader (intention seule)" : " · à venir");
    }
    TILES.forEach(function (tile,index) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "tile-target";
      button.dataset.tile = tile.id;
      button.setAttribute("aria-label", tile.label + (tile.enabled ? ", intention KOReader" : ", à venir"));
      position(button,tile);
      button.addEventListener("click",function () {
        focusTile(index);
        announce(tileAction(tile.id));
      });
      stage.appendChild(button);
      tileButtons.push(button);
    });

    position(statusBar,BAR);
    const controls = [];
    CONTROLS.forEach(function (id) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "status-control";
      button.dataset.control = id;
      button.title = CONTROL_NAMES[id] + " — simulation";
      button.setAttribute("aria-label", CONTROL_NAMES[id] + " (simulation uniquement)");
      button.addEventListener("click",function () { announce(quickAction(id)); });
      statusBar.appendChild(button);
      controls.push(button);
    });
    function renderStatus() {
      controls.forEach(function (button,index) {
        button.textContent = labelFor(CONTROLS[index], state);
      });
    }
    const presets = {
      unknown: defaults(),
      offline: {battery:74, charging:false,wifi:"off",frontlight:15,contrast:"normal"},
      connected: {battery:87,charging:false,wifi:"connected",frontlight:25,contrast:"normal"},
      charging: {battery:92,charging:true,wifi:"off",frontlight:10,contrast:"high"}
    };
    function choosePreset() {
      state = withSample(defaults(), presets[selection.value] || presets.unknown);
      batteryInput.value = state.battery === null ? 0 : state.battery;
      frontlightInput.value = state.frontlight === null ? 0 : state.frontlight;
      demoBadge.textContent = selection.options[selection.selectedIndex].text + " · fictif";
      renderStatus();
      display.textContent = "Valeurs de démonstration uniquement — aucun matériel interrogé.";
    }
    selection.addEventListener("change", choosePreset);
    batteryInput.addEventListener("input", function () {
      state = withSample(state, {battery:Number(batteryInput.value)});
      renderStatus();
    });
    frontlightInput.addEventListener("input", function () {
      state = withSample(state, {frontlight:Number(frontlightInput.value)});
      renderStatus();
    });
    stage.addEventListener("keydown",function (event) {
      if (["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key)) {
        event.preventDefault();
        focusTile(selectionIndex(focused,event.key));
      } else if (event.key === "Enter" && event.target === stage) {
        event.preventDefault();
        announce(tileAction(TILES[focused].id));
      }
    });
    document.getElementById("activate").addEventListener("click",function () {
      announce(tileAction(TILES[focused].id));
    });
    document.getElementById("reset").addEventListener("click",function () {
      selection.value = "unknown";
      choosePreset();
      focusTile(0);
    });
    focusTile(0);
    choosePreset();
  }

  const API = {WIDTH:WIDTH,HEIGHT:HEIGHT,TILES:TILES,CONTROLS:CONTROLS,BAR:BAR,
    defaults:defaults,withSample:withSample,labelFor:labelFor,
    tileAction:tileAction,quickAction:quickAction,selectionIndex:selectionIndex};
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (root && root.document) root.addEventListener("DOMContentLoaded",init);
})(typeof window !== "undefined" ? window : null);
