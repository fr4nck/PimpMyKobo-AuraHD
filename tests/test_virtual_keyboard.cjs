const test=require('node:test');
const assert=require('node:assert/strict');
const K=require('../experimental/shared/virtual_keyboard.js');
test('AZERTY and symbols fit six equal columns and include accents',()=>{
  for(const layout of ['letters','symbols']){
    const rows=K.rows(layout);
    assert.equal(rows.length,6);
    for(const row of rows)assert.equal(row.reduce((n,key)=>n+key.span,0),6);
  }
  const all=K.rows('letters').flat().map(k=>k.value);
  for(const key of ['a','z','e','r','t','y','é','è','à','ç'])
    assert.ok(all.includes(key),key);
  assert.equal(K.rows('letters',true)[0][0].value,'A');
  assert.ok(K.rows('letters',true).flat().some(key=>key.value==='É'));
});
test('insertion maintains selection, Unicode, space and newline',()=>{
  assert.deepEqual(K.edit('salut',1,4,'é',{maxLength:100}),
    {value:'sét',start:2,end:2,changed:true});
  assert.equal(K.edit('a',1,1,'space').value,'a ');
  assert.equal(K.edit('a',1,1,'enter').value,'a\n');
  assert.equal(K.edit('abc',1,1,'enter',{multiline:false}).action,'next');
});
test('backspace handles surrogate pairs and length bounds',()=>{
  assert.equal(K.edit('a😀b',3,3,'backspace').value,'ab');
  assert.equal(K.edit('abc',0,0,'backspace').changed,false);
  const rejected=K.edit('abc',3,3,'é',{maxLength:3});
  assert.equal(rejected.blocked,true);
  assert.equal(rejected.value,'abc');
});
test('invalid keys and dimensions are rejected',()=>{
  assert.throws(()=>K.rows('remote'));
  assert.throws(()=>K.edit('a',0,0,'abcdefghijklmnopq'));
  assert.throws(()=>K.edit('a',0,0,'b',{maxLength:200000}));
});
