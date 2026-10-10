const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8'),expected=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const elements={frame:{querySelector(){return {setAttribute(){}}},querySelectorAll(){return []}},seek:{},play:{},time:{}};
const context=vm.createContext({document:{getElementById:id=>elements[id]},requestAnimationFrame(){}});
vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1],context);
for(const sample of expected.samples){
  const offset=vm.runInContext(`offsetAt(${JSON.stringify(expected.track)},${sample.frame})`,context);
  offset.forEach((x,i)=>assert.ok(Math.abs(x-sample.offset[i])<1e-12));
  const swing=vm.runInContext(`walkSwing(${JSON.stringify(expected.performance)},${sample.frame})`,context);
  assert.ok(Math.abs(swing-sample.swing)<1e-10);
  for(const side of ['left','right']){
    const points=vm.runInContext(`walkLegPoints(${JSON.stringify(expected.performance)},${sample.frame},'${side}')`,context);
    points.forEach((x,i)=>assert.ok(Math.abs(x-sample.legs[side][i])<1e-10));
  }
}
console.log('staging: Python/JS offset and walk parity passed');
