const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../experimental/calculator-v01/calculator-core.js');
function close(actual,expected,epsilon=1e-10){assert.ok(Math.abs(actual-expected)<epsilon,actual+' != '+expected);}
test('scientific precedence, parentheses and right-associative powers',()=>{
  assert.equal(C.evaluate('2+3×4').value,14);
  assert.equal(C.evaluate('(2+3)×4').value,20);
  assert.equal(C.evaluate('-2^2').value,-4);
  assert.equal(C.evaluate('(-2)^2').value,4);
  assert.equal(C.evaluate('2^3^2').value,512);
  close(C.evaluate('2^-2').value,.25);
  assert.equal(C.evaluate('100×15%').value,15);
});
test('trigonometry, degrees/radians, logarithms and constants',()=>{
  close(C.evaluate('sin(30)').value,.5);
  close(C.evaluate('cos(60)').value,.5);
  close(C.evaluate('sin(π/2)',{mode:'RAD'}).value,1);
  close(C.evaluate('asin(0.5)').value,30);
  assert.equal(C.evaluate('sqrt(9)+log(100)').value,5);
  close(C.evaluate('ln(e)').value,1);
  close(C.evaluate('abs(-3)').value,3);
  assert.equal(C.evaluate('Ans×2',{ans:7}).value,14);
});
test('finite arithmetic and domain failures are not silently accepted',()=>{
  for(const expression of ['1/0','√(-1)','ln(0)','log(-10)','asin(2)',
    'tan(90)','1e999','9^999','(2+3','2 2','sin 10','2π',''])
    assert.throws(()=>C.evaluate(expression),expression);
});
test('malicious syntax, excessively large input and invalid modes fail closed',()=>{
  for(const expression of ['process.exit(1)','this.constructor','Math.random()',
    '{}','[]','2;alert(1)', '1,5','1/0;1','x'.repeat(1000)])
    assert.throws(()=>C.evaluate(expression),expression);
  assert.throws(()=>C.evaluate('2+2',{mode:'AUTO'}));
  assert.throws(()=>C.evaluate('2+2',{ans:Infinity}));
  assert.throws(()=>C.evaluate('('+ '1+'.repeat(60)+'1'+')'.repeat(1)));
});
test('formatted output never invents precision and no side effects occur',()=>{
  assert.equal(C.evaluate('2+2').text,'4');
  assert.equal(C.evaluate('1-1').text,'0');
  assert.equal(C.format(-0),'0');
  assert.equal(C.evaluate('1/3').text,'0.333333333333');
});
