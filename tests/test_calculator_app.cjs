/* Exercise the real Calculator app using synthetic DOM, no network. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const C=require('../experimental/calculator-v01/calculator-core.js');
const VK=require('../experimental/shared/virtual_keyboard.js');
const root=path.join(__dirname,'../experimental/calculator-v01');
function browser(){
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8'),elements=new Map();
 function element(id=''){
   return {id,value:'',textContent:'',hidden:false,dataset:{},children:[],listeners:{},
     selectionStart:0,selectionEnd:0,
     addEventListener(name,fn){this.listeners[name]=fn;},
     appendChild(c){this.children.push(c);},replaceChildren(){this.children=[];},
     setAttribute(){},focus(){},setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b;}};
 }
 for(const match of html.matchAll(/<[^>]+id="([^"]+)"[^>]*>/g))
   elements.set(match[1],element(match[1]));
 const document={getElementById:id=>elements.get(id),createElement:()=>element()};
 vm.runInNewContext(fs.readFileSync(path.join(root,'calculator-app.js'),'utf8'),{
   window:{PMKBCalculator:C,PMKBVirtualKeyboard:VK},document,console
 });
 return {get:id=>elements.get(id),
  press(key){const el=elements.get('calc-keys').children.find(x=>x.dataset.key===key);
    assert.ok(el,'No button '+key);el.listeners.click({target:el});},
  click(id){elements.get(id).listeners.click({});}};
}
test('scientific keypad calculates result, supports Ans and history',()=>{
 const b=browser();
 for(const key of ['2','+','3','×','4','equals'])b.press(key);
 assert.equal(b.get('calc-result').textContent,'14');
 assert.equal(b.get('calc-history').children.length,1);
 b.click('calc-clear');
 for(const key of ['Ans','+','1','equals'])b.press(key);
 assert.equal(b.get('calc-result').textContent,'15');
 assert.equal(b.get('calc-error').hidden,true);
});
test('angle switch and safe mathematical error are visible',()=>{
 const b=browser();
 for(const key of ['sin(','3','0',')','equals'])b.press(key);
 assert.equal(b.get('calc-result').textContent,'0.5');
 b.click('calc-angle');
 assert.equal(b.get('calc-angle').textContent,'RAD');
 b.click('calc-clear');
 for(const key of ['1','÷','0','equals'])b.press(key);
 assert.equal(b.get('calc-error').hidden,false);
 assert.match(b.get('calc-error').textContent,/Division par zéro/);
 b.click('calc-all-clear');
 assert.equal(b.get('calc-history').children.length,0);
 assert.equal(b.get('calc-error').hidden,true);
});
test('backspace, caret insertion and max input length use shared keyboard logic',()=>{
 const b=browser();
 b.press('1');b.press('2');b.press('backspace');
 assert.equal(b.get('calc-expression').value,'1');
 b.get('calc-expression').setSelectionRange(0,0);
 b.press('9');
 assert.equal(b.get('calc-expression').value,'91');
});
