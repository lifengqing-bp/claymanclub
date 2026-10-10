// Optional development suite: real Chromium DOM, SVG rasterization and native controls.
const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const output = path.resolve(root, process.env.BROWSER_TEST_OUTPUT || 'outputs/browser-tests');
let browser, thisRun;
before(async () => {
  fs.mkdirSync(output, {recursive:true});
  // Unique directories preserve earlier evidence and the renderer's no-overwrite rule.
  thisRun = fs.mkdtempSync(path.join(output, 'run-'));
  for (const [name, source] of [['v04','examples/timed-performances.json'], ['v03','examples/episode-001.json'], ['v02','tests/fixtures/episode-001-v02.json']]) {
    execFileSync(process.env.PYTHON || 'python3', ['-m','claymanclub','render',source,'--backend','stickfigure','--output',path.join(thisRun,name)], {cwd:root});
  }
  browser = await chromium.launch({headless:true, channel:'chromium'});
  fs.writeFileSync(path.join(thisRun,'environment.json'), JSON.stringify({browser:browser.version(),playwright:require('playwright/package.json').version,platform:process.platform,viewport:{width:1000,height:1100}},null,2));
  console.log(`Browser evidence: ${thisRun}`);
});
after(async () => {if (browser) await browser.close();});
async function open(t, name='v03', viewport={width:1000,height:1100}, clock=true) {
  const page = await browser.newPage({viewport, deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror', error=>errors.push(String(error)));
  page.on('console', msg=>{if(msg.type()==='error') errors.push(msg.text());});
  const requests=[];
  page.on('request', req=>{if(!req.url().startsWith('file:')) requests.push(req.url());});
  if(clock) {await page.clock.install({time:new Date('2026-01-01T00:00:00Z')}); await page.clock.pauseAt(new Date('2026-01-01T00:00:01Z'));}
  await page.goto(pathToFileURL(path.join(thisRun,name,'index.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  t.after(async()=>{await page.close(); assert.deepEqual(errors,[]); assert.deepEqual(requests,[]);});
  return page;
}
async function frame(page, value) {
  // Native range keyboard events; no calls to player functions or mutations of player state.
  const seek=page.locator('#seek');
  await seek.focus();
  const max=Number(await seek.getAttribute('max'));
  await seek.press(value>max/2?'End':'Home');
  for(let i=0;i<Math.min(value,max-value);i++) await seek.press(value>max/2?'ArrowLeft':'ArrowRight');
  assert.equal(await seek.inputValue(),String(value));
}
async function picture(page, name) {
  return page.locator('#frame svg').screenshot({path:path.join(thisRun,`${name}.png`)});
}
async function geometry(page) {
  return page.evaluate(()=>{
    const svg=document.querySelector('#frame svg'), world=svg.querySelector('[data-camera-world]');
    const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
    const m=world.getCTM();
    return {matrix:[m.a,m.b,m.c,m.d,m.e,m.f],svg:rect(svg),
      overlays:[...svg.children].filter(e=>e.tagName==='text').map(rect),
      controls:['play','seek','time'].map(id=>rect(document.getElementById(id))),
      circle:rect(world.querySelector('circle'))};
  });
}

test('camera rasterizes deterministically; geometry, overlays and clipping are stable', async t=>{
  const page=await open(t);
  const initial=await picture(page,'frame-000');
  const base=await geometry(page);
  const outside={x:Math.ceil(base.svg.x+base.svg.width)+1,y:Math.ceil(base.svg.y),width:20,height:Math.floor(base.svg.height)};
  const outsidePixels=await page.screenshot({clip:outside});
  await frame(page,90);
  const moved=await picture(page,'frame-090');
  const actual=await geometry(page);
  assert.notDeepEqual(moved,initial,'camera must change rendered pixels');
  assert.deepEqual(await page.screenshot({clip:outside}),outsidePixels,'scene clips to SVG viewport');
  assert.deepEqual(actual.overlays,base.overlays,'title/subtitle stay in screen coordinates');
  assert.deepEqual(actual.controls,base.controls,'camera cannot move fixed controls');
  // Independent analytic oracle for known keyframe: transform a real SVG point.
  const result=await page.evaluate(()=>{
    const world=document.querySelector('[data-camera-world]');
    const p=new DOMPoint(170,345).matrixTransform(world.getCTM());
    return [p.x,p.y];
  });
  const a=5*Math.PI/180, x=170-193.2, y=345-432;
  const expected=[270+1.2*(Math.cos(a)*x-Math.sin(a)*y),480+1.2*(Math.sin(a)*x+Math.cos(a)*y)];
  // getCTM includes the SVG viewport scale, unlike the camera's local matrix.
  const scale=actual.svg.height/960;
  expected.forEach((v,i)=>assert.ok(Math.abs(result[i]-v*scale)<0.01));
  assert.ok(actual.circle.x>base.circle.x && actual.circle.width>base.circle.width);
  // Fixed overlays are compared as pixels, not just DOM bounding boxes.
  for (const [name,y,height] of [['title',0,100],['subtitle',790,130]]) {
    const clip={x:actual.svg.x,y:actual.svg.y+y*scale,width:actual.svg.width,height:height*scale};
    const at90=await page.screenshot({clip});
    await frame(page,0);
    assert.deepEqual(await page.screenshot({clip}),at90,`${name} pixels must remain stable`);
    await frame(page,90);
  }
  let previous;
  for(const f of [89,90,91]) {
    await frame(page,f);
    const g=await geometry(page);
    await picture(page,`frame-${f}`);
    if(previous) assert.ok(Math.hypot(g.circle.x-previous.x,g.circle.y-previous.y)<4,'no position jump around keyframe');
    previous=g.circle;
  }
  await frame(page,179); await picture(page,'frame-179');
  await frame(page,180); await picture(page,'frame-180');
  assert.match(await page.locator('#frame').textContent(),/我只是/);
  await frame(page,90);
  assert.deepEqual(await picture(page,'frame-090-return'),moved,'backward seek across a cut is pixel exact');
  await page.reload(); await frame(page,90);
  assert.deepEqual(await picture(page,'frame-090-reload'),moved,'reload yields identical pixels');
});

test('native play, pause, drag, backward seek, cuts and replay',async t=>{
  const page=await open(t);
  const button=page.locator('#play'), seek=page.locator('#seek');
  const initial=await picture(page,'controls-start');
  await button.click(); await page.clock.runFor(1550);
  const at=Number(await seek.inputValue()); assert.ok(at>=45 && at<=47);
  await button.click(); const paused=await picture(page,'paused');
  await page.clock.runFor(1000); assert.equal(Number(await seek.inputValue()),at);
  assert.deepEqual(await picture(page,'paused-later'),paused);
  await frame(page,at); assert.deepEqual(await picture(page,'seek-playback-parity'),paused);
  const box=await seek.boundingBox();
  await page.mouse.move(box.x+box.width*0.25,box.y+box.height/2);
  await page.mouse.down(); await page.mouse.move(box.x+box.width*0.6,box.y+box.height/2,{steps:8}); await page.mouse.up();
  assert.ok(Number(await seek.inputValue())>450,'native pointer drag updates frame');
  await frame(page,179); await button.click(); await page.clock.runFor(80);
  assert.match(await page.locator('#frame').textContent(),/我只是/);
  await button.click(); await frame(page,898); await button.click(); await page.clock.runFor(150);
  assert.equal(await seek.inputValue(),'899'); assert.equal(await button.textContent(),'播放');
  await picture(page,'frame-899');
  await button.click(); assert.equal(await seek.inputValue(),'0');
  assert.deepEqual(await picture(page,'replay'),initial);
  await page.clock.runFor(100); assert.ok(Number(await seek.inputValue())>0);
});

test('unmocked requestAnimationFrame advances and pauses in Chromium; v0.2 still plays',async t=>{
  const page=await open(t,'v02',undefined,false);
  await page.locator('#play').click();
  await page.waitForFunction(()=>Number(document.getElementById('seek').value)>=3);
  await page.locator('#play').click();
  const value=await page.locator('#seek').inputValue();
  const before=await picture(page,'legacy-paused');
  await page.waitForTimeout(150);
  assert.equal(await page.locator('#seek').inputValue(),value);
  assert.deepEqual(await picture(page,'legacy-paused-later'),before);
});

test('narrow viewport keeps the whole SVG and controls reachable',async t=>{
  const page=await open(t,'v03',{width:390,height:844});
  await frame(page,90);
  await page.screenshot({path:path.join(thisRun,'mobile-frame-090.png'),fullPage:true});
  const g=await geometry(page);
  assert.ok(g.svg.x>=0 && g.svg.x+g.svg.width<=390,'SVG viewport fits screen');
  assert.ok(Math.abs(g.svg.width/g.svg.height-540/960)<0.001,'SVG viewport retains portrait ratio without internal letterboxing');
  for(const r of g.overlays) assert.ok(r.x>=g.svg.x && r.x+r.width<=g.svg.x+g.svg.width,'overlay text is not cropped');
  await page.locator('#play').click(); await page.clock.runFor(100);
  assert.ok(Number(await page.locator('#seek').inputValue())>90);
});


test('timed performances switch at exclusive boundaries and replay deterministically',async t=>{
  const page=await open(t,'v04');
  const content=()=>page.locator('#frame').textContent();
  const empty=await picture(page,'timed-000');
  await frame(page,19); assert.doesNotMatch(await content(),/我的充电器|等等/);
  await frame(page,20); assert.match(await content(),/我的充电器/);
  const first=await picture(page,'timed-020');
  await frame(page,119); assert.match(await content(),/我的充电器/);
  await frame(page,120); assert.match(await content(),/等等/);
  assert.doesNotMatch(await content(),/我的充电器/);
  const second=await picture(page,'timed-120');
  await frame(page,170); assert.doesNotMatch(await content(),/我的充电器|等等/);
  await frame(page,200); assert.match(await content(),/我只是/);
  await frame(page,120); assert.deepEqual(await picture(page,'timed-backward'),second);
  await frame(page,20); assert.deepEqual(await picture(page,'timed-first-return'),first);
  await frame(page,119); await page.locator('#play').click(); await page.clock.runFor(80);
  await page.locator('#play').click(); assert.match(await content(),/等等/);
  const at=Number(await page.locator('#seek').inputValue());
  const played=await picture(page,'timed-played');
  await frame(page,0); await frame(page,at);
  assert.deepEqual(await picture(page,'timed-seek-parity'),played);
  await frame(page,899); await page.locator('#play').click();
  assert.equal(await page.locator('#seek').inputValue(),'0');
  assert.deepEqual(await picture(page,'timed-replay'),empty);
  await page.reload(); await frame(page,120);
  assert.deepEqual(await picture(page,'timed-reload'),second);
});
