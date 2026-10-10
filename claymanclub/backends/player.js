// Pure absolute-frame functions: playback and seeking share the same path.
function cameraAt(camera, frame) {
  if (!camera) return {position:[0,0,0],rotation:[0,0,0],zoom:1};
  let left=camera.keyframes[0], right=left;
  for (const key of camera.keyframes) {
    right=key;
    if (frame<=key.frame) break;
    left=key;
  }
  const span=right.frame-left.frame;
  const a=span ? Math.max(0,Math.min(1,(frame-left.frame)/span)) : 0;
  const lerp=(x,y)=>(1-a)*x+a*y;
  return {position:left.position.map((x,i)=>lerp(x,right.position[i])),
    rotation:left.rotation.map((x,i)=>lerp(x,right.rotation[i])),zoom:lerp(left.zoom,right.zoom)};
}
function cameraTransform(state) {
  // Inverse camera pose, converted from y-up stage units to y-down SVG units.
  const [x,y]=state.position;
  return `translate(270 480) scale(${state.zoom}) rotate(${state.rotation[2]}) translate(${-270-x*960} ${-480+y*960})`;
}
function nodAmount(performance, frame) {
  if (!performance || performance.action!=='nod') return 0;
  const start=performance.start_frame,end=performance.end_frame;
  if(frame<=start || frame>=end-1) return 0;
  return (1-Math.cos(2*Math.PI*(frame-start)/(end-start-1)))/2;
}
const picture=document.getElementById('frame'),seek=document.getElementById('seek'),button=document.getElementById('play');
let playing=false,t=0,last=null,currentShot=null,currentPose=null;
seek.max=plan.duration_frames-1;
function draw() {
  const f=Math.max(0,Math.min(plan.duration_frames-1,Math.floor(t)));
  const s=plan.shots.find(s=>f>=s.start&&f<s.end);
  const local=f-s.start;
  const pose=s.poses ? s.poses.reduce((chosen,p)=>p.start<=local?p:chosen,s.poses[0]) : s;
  if(currentShot!==s || currentPose!==pose){picture.innerHTML=pose.svg;currentShot=s;currentPose=pose;}
  picture.querySelector('[data-camera-world]').setAttribute('transform',cameraTransform(cameraAt(s.camera,f-s.start)));
  if(s.motions){
    for(const head of picture.querySelectorAll('[data-head]')){
      const p=s.motions.find(p=>p.actor===head.getAttribute('data-head') && p.start_frame<=local && local<p.end_frame);
      head.setAttribute('transform',`translate(0 ${15*nodAmount(p,local)})`);
    }
  }
  seek.value=f;
  document.getElementById('time').textContent=(f/plan.fps).toFixed(1)+'s';
}
button.onclick=()=>{
  if(!playing && t>=plan.duration_frames-1)t=0;
  playing=!playing;last=null;button.textContent=playing?'暂停':'播放';draw();
};
seek.oninput=()=>{t=Number(seek.value);last=null;draw();};
function tick(now){
  if(playing&&last!==null){
    t+=(now-last)*plan.fps/1000;
    if(t>=plan.duration_frames-1){t=plan.duration_frames-1;playing=false;button.textContent='播放';}
    draw();
  }
  last=now;requestAnimationFrame(tick);
}
draw();requestAnimationFrame(tick);
