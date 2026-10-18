/* PMKB calculator UI — offline only, shared caret engine, no persistent service. */
(function(){
"use strict";
const C=window.PMKBCalculator,VK=window.PMKBVirtualKeyboard;
if(!C||!VK)throw Error("Moteur de calcul ou clavier PMKB absent");
const $=id=>document.getElementById(id);
const expression=$("calc-expression"),result=$("calc-result"),error=$("calc-error");
let mode="DEG",ans=0;
const history=[];
const layout=[
  [["sin","sin("],["cos","cos("],["tan","tan("],["ln","ln("],["log","log("],["√","√("]],
  [["7","7"],["8","8"],["9","9"],["÷","÷"],["(","("],[")",")"]],
  [["4","4"],["5","5"],["6","6"],["×","×"],["^","^"],["π","π"]],
  [["1","1"],["2","2"],["3","3"],["−","−"],["%","%"],["e","e"]],
  [["0","0"],[".", "."],["Ans","Ans"],["+","+"],["⌫","backspace"],["=","equals"]]
];
function setError(message){error.textContent=message;error.hidden=!message;}
function calculate(){
  try{
    const evaluated=C.evaluate(expression.value,{mode,ans});
    result.textContent=evaluated.text;
    ans=evaluated.value;
    history.unshift({expression:expression.value,value:evaluated.text,mode});
    if(history.length>8)history.pop();
    const list=$("calc-history");
    list.replaceChildren();
    for(const item of history){
      const li=document.createElement("li");
      li.textContent=item.expression+" = "+item.value+" ("+item.mode+")";
      list.appendChild(li);
    }
    setError("");
  }catch(err){setError(err.message);}
}
function press(key){
  if(key==="equals"){calculate();return;}
  const edited=VK.edit(expression.value,expression.selectionStart,expression.selectionEnd,key,
    {maxLength:C.MAX_EXPRESSION,multiline:false});
  if(edited.blocked){setError("Expression trop longue (192 caractères).");return;}
  if(edited.changed){
    expression.value=edited.value;
    expression.setSelectionRange?.(edited.start,edited.end);
    setError("");
  }
  expression.focus();
}
const panel=$("calc-keys");
for(const row of layout){
  for(const [label,key] of row){
    const button=document.createElement("button");
    button.type="button";button.textContent=label;
    button.dataset.key=key;button.setAttribute("aria-label",label);
    button.addEventListener("pointerdown",event=>event.preventDefault());
    button.addEventListener("click",()=>press(key));
    panel.appendChild(button);
  }
}
$("calc-angle").addEventListener("click",()=>{
  mode=mode==="DEG"?"RAD":"DEG";
  $("calc-angle").textContent=mode;setError("");
});
$("calc-clear").addEventListener("click",()=>{
  expression.value="";result.textContent="0";setError("");expression.focus();
});
$("calc-all-clear").addEventListener("click",()=>{
  expression.value="";result.textContent="0";ans=0;history.length=0;
  $("calc-history").replaceChildren();setError("");expression.focus();
});
expression.addEventListener("input",()=>setError(""));
expression.addEventListener("keydown",event=>{
  if(event.key==="Enter"){event.preventDefault();calculate();}
});
})();
