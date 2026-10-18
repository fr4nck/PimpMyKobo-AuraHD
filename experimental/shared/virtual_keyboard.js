/* PMKB virtual keyboard V0: pure AZERTY model, no DOM or I/O. */
(function(root){
"use strict";
const azerty=[
["a","z","e","r","t","y"],["u","i","o","p","q","s"],
["d","f","g","h","j","k"],["l","m","w","x","c","v"],
["b","n","é","è","à","ç"]];
const symbols=[
["1","2","3","4","5","6"],["7","8","9","0",".",","],
["+","-","*","/","=","%"],["(",")","[","]",":",";"],
["!","?","€","@","#","_"]];
function rows(page="letters",shift=false){
  if(!["letters","symbols"].includes(page)||typeof shift!=="boolean")
    throw Error("Disposition inconnue");
  const source=page==="letters"?azerty:symbols;
  const layout=source.map(row=>row.map(key=>{
    const value=shift&&page==="letters"?key.toLocaleUpperCase("fr"):key;
    return {key,value,label:value,aria:value,span:1};
  }));
  layout.push([
    {key:"shift",value:null,label:"⇧",aria:"Majuscules",span:1},
    {key:"page",value:null,label:page==="letters"?"123":"ABC",
      aria:page==="letters"?"Chiffres et symboles":"Retour aux lettres",span:1},
    {key:"space",value:null,label:"Espace",aria:"Insérer une espace",span:2},
    {key:"backspace",value:null,label:"⌫",aria:"Effacer",span:1},
    {key:"enter",value:null,label:"↵",aria:"Retour",span:1}
  ]);
  return layout;
}
function clamp(n,length){
  return Number.isFinite(n)?Math.max(0,Math.min(length,Math.trunc(n))):length;
}
function previous(text,pos){
  return pos>1&&text.charCodeAt(pos-1)>=0xDC00&&text.charCodeAt(pos-1)<=0xDFFF&&
    text.charCodeAt(pos-2)>=0xD800&&text.charCodeAt(pos-2)<=0xDBFF?pos-2:Math.max(0,pos-1);
}
function edit(value,start,end,key,{maxLength=120000,multiline=true}={}){
  if(typeof value!=="string"||typeof key!=="string")throw Error("Saisie invalide");
  if(!Number.isInteger(maxLength)||maxLength<1||maxLength>120000)throw Error("Limite invalide");
  let a=clamp(start,value.length),b=clamp(end,value.length);
  if(a>b)[a,b]=[b,a];
  if(key==="enter"&&!multiline)return {value,start:a,end:b,changed:false,action:"next"};
  if(key==="backspace"&&a===b)a=previous(value,a);
  const inserted=key==="backspace"?"":key==="space"?" ":key==="enter"?"\n":key;
  if(inserted.length>16||inserted.includes("\u0000")||(!multiline&&inserted.includes("\n")))
    throw Error("Touche invalide");
  const next=value.slice(0,a)+inserted+value.slice(b);
  if(next.length>maxLength)return {value,start:a,end:b,changed:false,blocked:true};
  const caret=a+inserted.length;
  return {value:next,start:caret,end:caret,changed:next!==value};
}
const API={rows,edit};
if(typeof module!=="undefined"&&module.exports)module.exports=API;
if(root&&root.document)root.PMKBVirtualKeyboard=API;
})(typeof window!=="undefined"?window:null);
