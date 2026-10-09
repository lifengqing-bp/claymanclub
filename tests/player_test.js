// Node's built-in VM only; no browser automation or npm packages required.
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const expected=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const world={setAttribute(name,value){this[name]=value;}};
const elements={frame:{innerHTML:'',querySelector(){return world;}},seek:{value:0},play:{},time:{}};
const context=vm.createContext({document:{getElementById:id=>elements[id]},requestAnimationFrame(){}});
vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1],context);
const run=source=>vm.runInContext(source,context);
const seek=frame=>{elements.seek.value=frame;elements.seek.oninput();return world.transform;};
// Compare the actual player sampler with the Python reference across all shots.
for(const item of expected){
  const actual=run(`cameraAt(plan.shots[${item.shot}].camera,${item.frame})`);
  for(const key of ['position','rotation','zoom']){
    const a=Array.isArray(item.state[key])?actual[key]:[actual[key]];
    const b=Array.isArray(item.state[key])?item.state[key]:[item.state[key]];
    b.forEach((value,i)=>assert.ok(Math.abs(a[i]-value)<1e-10));
  }
}
const target=seek(45);
seek(0);elements.play.onclick();run('tick(1000);tick(2500)');
assert.equal(world.transform,target); // 1.5 seconds * 30fps
assert.equal(Number(elements.seek.value),45);
elements.play.onclick();run('tick(9000)');assert.equal(world.transform,target); // paused
seek(130);seek(45);assert.equal(world.transform,target); // backward seek
const boundary=seek(180);assert.notEqual(boundary,target);
assert.equal(boundary,'translate(270 480) scale(1) rotate(0) translate(-270 -480)');
assert.match(elements.frame.innerHTML,/我只是/);
seek(179);elements.play.onclick();run('tick(10000);tick(10040)');
assert.equal(world.transform,boundary); // cross shot boundary while playing
seek(899);run('tick(11000);tick(12000)');assert.equal(run('playing'),false);
elements.play.onclick();assert.equal(Number(elements.seek.value),0); // replay
console.log('player: interpolation, playback, pause, seek, shot boundary and replay passed');
