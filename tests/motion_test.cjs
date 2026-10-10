const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const expected=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const elements={frame:{querySelector(){return {setAttribute(){}};},querySelectorAll(){return [];}},seek:{},play:{},time:{}};
const context=vm.createContext({document:{getElementById:id=>elements[id]},requestAnimationFrame(){}});
vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1],context);
for(const sample of expected.samples){
  const fn=expected.gestures?'gestureAngles':'nodAmount';
  const actual=vm.runInContext(`${fn}(${JSON.stringify(expected.performance)},${sample.frame})`,context);
  if(expected.gestures){
    for(const joint of ['wave','bow']) assert.ok(Math.abs(actual[joint]-sample.angles[joint])<1e-10);
  }else assert.ok(Math.abs(actual-sample.amount)<1e-12);
}
console.log('motion: Python/JavaScript motion parity passed');
