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
function motionEnvelope(performance, frame) {
  if (!performance || !['nod','wave','bow','walk'].includes(performance.action)) return 0;
  const start=performance.start_frame,end=performance.end_frame;
  if(frame<=start || frame>=end-1) return 0;
  return (1-Math.cos(2*Math.PI*(frame-start)/(end-start-1)))/2;
}
function nodAmount(performance, frame) {
  return performance && performance.action==='nod' ? motionEnvelope(performance,frame) : 0;
}
function gestureAngles(performance, frame) {
  const amount=motionEnvelope(performance,frame);
  const bow=performance && performance.action==='bow' ? 30*amount : 0;
  let wave=0;
  if(performance && performance.action==='wave' && amount){
    const phase=(frame-performance.start_frame)/(performance.end_frame-performance.start_frame-1);
    let lift=Math.min(1,4*phase,4*(1-phase));
    lift=lift*lift*(3-2*lift);
    wave=-55*lift;
  }
  return {bow,wave};
}
function offsetAt(track, frame) {
  if(!track) return [0,0,0];
  let left=track.keyframes[0],right=left;
  for(const key of track.keyframes){right=key;if(frame<=key.frame)break;left=key;}
  const span=right.frame-left.frame;
  const a=span?Math.max(0,Math.min(1,(frame-left.frame)/span)):0;
  return left.offset.map((v,i)=>(1-a)*v+a*right.offset[i]);
}
function walkSwing(p,frame){
  if(!p || p.action!=='walk')return 0;
  const amount=motionEnvelope(p,frame);
  if(!amount)return 0;
  return 22*Math.sin(4*Math.PI*(frame-p.start_frame)/(p.end_frame-p.start_frame-1))*amount;
}
function jointAngles(p,frame){
  const result={elbow_left:0,elbow_right:0,knee_left:0,knee_right:0};
  const amount=motionEnvelope(p,frame);
  if(!amount)return result;
  const phase=(frame-p.start_frame)/(p.end_frame-p.start_frame-1);
  if(p.action==='wave'){
    let lift=Math.min(1,4*phase,4*(1-phase));lift=lift*lift*(3-2*lift);
    result.elbow_right=-85*lift+20*Math.sin(8*Math.PI*phase)*amount;
  }else if(p.action==='walk'){
    const stride=Math.sin(4*Math.PI*phase);
    result.elbow_left=35*amount;result.elbow_right=-35*amount;
    result.knee_left=70*Math.max(0,-stride)*amount;
    result.knee_right=-70*Math.max(0,stride)*amount;
  }
  return result;
}
function walkLegPoints(p,frame,side){
  const dx=side==='left'?-20:20,angle=jointAngles(p,frame)['knee_'+side]*Math.PI/180;
  return [dx,580,dx+dx*Math.cos(angle)-55*Math.sin(angle),580+dx*Math.sin(angle)+55*Math.cos(angle)];
}
function stageActors(shot,frame){
  const offsets=Object.fromEntries(shot.cast.map(a=>[a,offsetAt(shot.actor_tracks.find(t=>t.actor===a),frame)]));
  const stageX=a=>(shot.cast.length===1?270:170+shot.cast.indexOf(a)*200)+960*offsets[a][0];
  for(const actor of picture.querySelectorAll('[data-actor]')){
    const id=actor.getAttribute('data-actor'),[x,y]=offsets[id];
    actor.setAttribute('transform',`translate(${Number(actor.getAttribute('data-base-x'))+x*960} ${-y*960})`);
    const p=shot.performances.find(p=>p.actor===id && p.start_frame<=frame && frame<p.end_frame);
    const target=p && (p.gaze_target || (p.action==='look_at_partner'?shot.cast.find(a=>a!==id):null));
    const gaze=target?6*Math.sign(stageX(target)-stageX(id)):0;
    const eyes=actor.querySelector('[data-eyes]'),headY=Number(eyes.getAttribute('data-head-y'));
    eyes.setAttribute('d',`M${-15+gaze} ${headY-5}h1M${15+gaze} ${headY-5}h1`);
    const swing=walkSwing(p,frame);
    actor.querySelector('[data-walk-arm]').setAttribute('transform',`rotate(${-swing} 0 425)`);
    actor.querySelector('[data-wave]').setAttribute('transform',`rotate(${gestureAngles(p,frame).wave+swing} 0 425)`);
    for(const leg of actor.querySelectorAll('[data-walk-leg]')){
      const side=leg.getAttribute('data-walk-leg');
      leg.setAttribute('transform',`rotate(${side==='left'?swing:-swing} 0 525)`);
    }
  }
  for(const name of picture.querySelectorAll('[data-name]')){
    const [x,y]=offsets[name.getAttribute('data-name')];
    name.setAttribute('transform',`translate(${x*960} ${-y*960})`);
  }
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
      const joints=gestureAngles(p,local),upper=head.parentElement;
      const bends=jointAngles(p,local);
      for(const joint of upper.parentElement.querySelectorAll('[data-bend]')){
        const key=joint.getAttribute('data-bend')+'_'+joint.getAttribute('data-side');
        joint.setAttribute('transform',`rotate(${bends[key]} ${joint.getAttribute('data-joint-x')} ${joint.getAttribute('data-joint-y')})`);
      }
      upper.setAttribute('transform',`rotate(${joints.bow} 0 525)`);
      upper.querySelector('[data-wave]').setAttribute('transform',`rotate(${joints.wave} 0 425)`);
    }
  }
  if(s.actor_tracks)stageActors(s,local);
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
