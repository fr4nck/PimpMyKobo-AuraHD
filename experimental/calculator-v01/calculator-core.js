/* PMKB Scientific Calculator V0 — offline expression parser, no eval or I/O. */
(function(root){
"use strict";
const MAX_EXPRESSION=192,MAX_TOKENS=128,MAX_DEPTH=48;
const number=/^(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/;
const identifier=/^[a-zA-Z]+/;
function fail(message){throw Error(message);}
function finite(n){if(!Number.isFinite(n))fail("Résultat non fini ou hors limites");return n;}
function tokens(expression){
  if(typeof expression!=="string"||!expression.trim()||
     expression.length>MAX_EXPRESSION)fail("Expression vide ou trop longue");
  const result=[];
  let i=0;
  while(i<expression.length){
    const rest=expression.slice(i),char=rest[0];
    if(/\s/.test(char)){i++;continue;}
    let match;
    if((match=rest.match(number))){
      const value=Number(match[0]);finite(value);
      result.push({type:"number",value});i+=match[0].length;
    }else if((match=rest.match(identifier))){
      result.push({type:"name",value:match[0].toLowerCase()});i+=match[0].length;
    }else if(char==="π"||char==="√"){
      result.push({type:"name",value:char==="π"?"pi":"sqrt"});i++;
    }else if("+-*/^()%−×÷".includes(char)){
      const normalized={"−":"-","×":"*","÷":"/"}[char]||char;
      result.push({type:"operator",value:normalized});i++;
    }else fail("Caractère interdit dans l'expression");
    if(result.length>MAX_TOKENS)fail("Expression trop complexe");
  }
  return result;
}
function format(value){
  finite(value);
  if(Object.is(value,-0)||value===0)return "0";
  return Number(value.toPrecision(12)).toString();
}
function evaluate(expression,{mode="DEG",ans=0}={}){
  if(!["DEG","RAD"].includes(mode))fail("Mode d'angle invalide");
  if(typeof ans!=="number"||!Number.isFinite(ans))fail("Mémoire invalide");
  const stream=tokens(expression);let pos=0;
  const peek=()=>stream[pos]?.value;
  function take(expected){
    if(peek()!==expected)fail("Parenthèse ou opérateur manquant");
    return stream[pos++];
  }
  function functionValue(name,value){
    const angle=mode==="DEG"?value*Math.PI/180:value;
    switch(name){
      case "sin":return finite(Math.sin(angle));
      case "cos":return finite(Math.cos(angle));
      case "tan":
        if(Math.abs(Math.cos(angle))<1e-12)fail("Tangente indéfinie");
        return finite(Math.tan(angle));
      case "asin":
        if(value<-1||value>1)fail("Domaine inverse trigonométrique");
        return finite(Math.asin(value)*(mode==="DEG"?180/Math.PI:1));
      case "acos":
        if(value<-1||value>1)fail("Domaine inverse trigonométrique");
        return finite(Math.acos(value)*(mode==="DEG"?180/Math.PI:1));
      case "atan":return finite(Math.atan(value)*(mode==="DEG"?180/Math.PI:1));
      case "ln":if(value<=0)fail("Logarithme hors domaine");return finite(Math.log(value));
      case "log":if(value<=0)fail("Logarithme hors domaine");return finite(Math.log10(value));
      case "sqrt":if(value<0)fail("Racine négative");return finite(Math.sqrt(value));
      case "abs":return finite(Math.abs(value));
      default:fail("Fonction inconnue");
    }
  }
  function parse(minPower=0,depth=0){
    if(depth>MAX_DEPTH)fail("Expression trop imbriquée");
    const token=stream[pos++];
    if(!token)fail("Expression incomplète");
    let left;
    if(token.type==="number")left=token.value;
    else if(token.value==="("){
      left=parse(0,depth+1);
      take(")");
    }else if(token.value==="+"||token.value==="-"){
      const v=parse(35,depth+1);
      left=token.value==="-"?-v:v;
    }else if(token.type==="name"){
      if(token.value==="pi")left=Math.PI;
      else if(token.value==="e")left=Math.E;
      else if(token.value==="ans")left=ans;
      else {
        take("(");
        const argument=parse(0,depth+1);
        take(")");
        left=functionValue(token.value,argument);
      }
    }else fail("Nombre ou parenthèse attendu");
    left=finite(left);
    for(;;){
      const op=peek();
      if(op==="%"&&45>=minPower){
        pos++;left=finite(left/100);continue;
      }
      const powers={"+":[10,11],"-":[10,11],"*":[20,21],"/":[20,21],"^":[40,40]};
      const binding=powers[op];
      if(!binding||binding[0]<minPower)break;
      pos++;
      const right=parse(binding[1],depth+1);
      if(op==="+")left=left+right;
      else if(op==="-")left=left-right;
      else if(op==="*")left=left*right;
      else if(op==="/"){
        if(right===0)fail("Division par zéro");
        left=left/right;
      }else left=Math.pow(left,right);
      left=finite(left);
    }
    return left;
  }
  const value=finite(parse());
  if(pos!==stream.length)fail("Expression incorrecte");
  const normalized=Object.is(value,-0)?0:value;
  return {value:normalized,text:format(normalized),mode};
}
const API={evaluate,format,MAX_EXPRESSION};
if(typeof module!=="undefined"&&module.exports)module.exports=API;
if(root&&root.document)root.PMKBCalculator=API;
})(typeof window!=="undefined"?window:null);
