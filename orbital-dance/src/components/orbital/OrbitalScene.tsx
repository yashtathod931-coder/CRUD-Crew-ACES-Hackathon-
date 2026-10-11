import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Environment, Lightformer, Line, OrbitControls } from '@react-three/drei';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import type { OrbitControls as Controls } from 'three-stdlib';
import { sampleSimulation, type Vec3 } from '@/sim/simulation';
import { useSimulation } from '@/sim/store';

type Palette = Record<'primary'|'violet'|'destructive'|'warning'|'ocean'|'land'|'cloud'|'night'|'metal'|'solar'|'visor', string>;
function readPalette(): Palette {
  const names = ['primary','violet','destructive','warning','ocean','land','cloud','night','metal','solar','visor'] as const;
  const css = getComputedStyle(document.documentElement);
  const canvas = document.createElement('canvas'); canvas.width=1; canvas.height=1;
  const ctx = canvas.getContext('2d', {willReadFrequently:true});
  return Object.fromEntries(names.map(name => {
    const token = ['primary','violet','destructive','warning'].includes(name) ? name : `scene-${name}`;
    if (!ctx) return [name, 'gray'];
    ctx.fillStyle=css.getPropertyValue(`--${token}`).trim(); ctx.fillRect(0,0,1,1);
    const [r,g,b]=ctx.getImageData(0,0,1,1).data;
    return [name, `rgb(${r},${g},${b})`];
  })) as Palette;
}
const vertex = `varying vec3 vNormal; varying vec3 vPos; varying vec3 vWorld;
void main(){vNormal=normalize(normalMatrix*normal);vPos=position;vWorld=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
const earthFragment = `
uniform vec3 ocean; uniform vec3 land; uniform vec3 cloud; uniform vec3 night;
varying vec3 vNormal; varying vec3 vPos; varying vec3 vWorld;
float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float noise(vec3 p){vec3 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){return .55*noise(p)+.26*noise(p*2.1)+.13*noise(p*4.2)+.06*noise(p*8.4);}
void main(){vec3 p=normalize(vPos);float terrain=fbm(p*3.8+vec3(2.7,1.3,.8));float continent=smoothstep(.48,.53,terrain);
vec3 base=mix(ocean,land*(.72+terrain*.55),continent); float clouds=smoothstep(.57,.72,fbm(p*9.+vec3(5.)));base=mix(base,cloud,clouds*.7);
float ice=smoothstep(.88,.98,abs(p.y));base=mix(base,cloud,ice*.8);
float lit=max(0.,dot(vNormal,normalize(vec3(-.6,.7,1.))));float day=smoothstep(-.05,.4,dot(vNormal,normalize(vec3(-.6,.7,1.))));
vec3 color=mix(night*.55,base*(.4+lit*.8),day);float cities=step(.965,noise(p*150.))*continent*(1.-day);color+=cloud*cities*.65;
float rim=pow(1.-max(0.,dot(vNormal,vec3(0,0,1))),3.);color+=ocean*rim*.8;gl_FragColor=vec4(color,1.);}`;
function Earth({ p }: {p:Palette}) {
  const group=useRef<THREE.Group>(null);
  const uniforms=useMemo(()=>Object.fromEntries(['ocean','land','cloud','night'].map(k=>[k,{value:new THREE.Color(p[k as keyof Palette])}])),[p]);
  useFrame((_,delta)=>{if(group.current && useSimulation.getState().playing) group.current.rotation.y+=Math.min(delta,.05)*.018;});
  return <group ref={group} rotation={[.08,-.5,.14]}>
    <mesh><sphereGeometry args={[1.82,64,48]}/><shaderMaterial vertexShader={vertex} fragmentShader={earthFragment} uniforms={uniforms}/></mesh>
    <mesh><sphereGeometry args={[1.87,48,32]}/><shaderMaterial vertexShader={vertex} fragmentShader={`uniform vec3 glow; varying vec3 vNormal; void main(){float rim=pow(1.-abs(dot(normalize(vNormal),vec3(0,0,1))),3.2);gl_FragColor=vec4(glow,rim*.65);}`} uniforms={{glow:{value:new THREE.Color(p.primary)}}} transparent depthWrite={false} blending={THREE.AdditiveBlending}/></mesh>
    <mesh><sphereGeometry args={[1.95,40,32]}/><shaderMaterial vertexShader={vertex} fragmentShader={`uniform vec3 glow; varying vec3 vNormal; void main(){float rim=pow(1.-abs(dot(normalize(vNormal),vec3(0,0,1))),5.);gl_FragColor=vec4(glow,rim*.12);}`} uniforms={{glow:{value:new THREE.Color(p.primary)}}} transparent depthWrite={false} blending={THREE.AdditiveBlending}/></mesh>
  </group>;
}
const orbitPoint=(angle:number,r:number,inclination:number):Vec3=>[r*Math.cos(angle),r*Math.sin(angle)*Math.sin(inclination),r*Math.sin(angle)*Math.cos(inclination)];
function ObjectLabel({object,name,detail,debris=false}:{object:React.RefObject<THREE.Group|null>;name:string;detail:string;debris?:boolean}) {
  const element=useRef<HTMLDivElement|null>(null);const point=useMemo(()=>new THREE.Vector3(),[]);
  const {camera,size,gl}=useThree();
  useEffect(()=>{const parent=gl.domElement.parentElement;if(!parent)return;const label=document.createElement('div');label.className=`object-label ${debris?'debris-label':''}`;label.append(document.createTextNode(name),document.createElement('br'));const small=document.createElement('small');small.textContent=detail;label.append(small);label.style.position='absolute';label.style.top='0';label.style.left='0';label.style.zIndex='2';parent.append(label);element.current=label;return()=>{label.remove();element.current=null;};},[gl,name,detail,debris]);
  useFrame(()=>{const label=element.current;const group=object.current;if(!label||!group)return;group.getWorldPosition(point);point.y+=.32;point.project(camera);const x=(point.x*.5+.5)*size.width,y=(-point.y*.5+.5)*size.height;label.style.display=group.visible && x>20 && x<size.width-135 && y>70 && y<size.height-120?'block':'none';label.style.transform=`translate(${x}px,${y}px)`;});
  return null;
}
function Satellite({index,p}:{index:number;p:Palette}) {
  const ref=useRef<THREE.Group>(null); const exhaust=useRef<THREE.Mesh>(null); const halo=useRef<THREE.Mesh>(null);
  const names=['SENTINEL-1A','AURORA-03','RELAY-07','ATLAS-02'];
  useFrame(()=>{
    const s=useSimulation.getState().snapshot;
    if(!ref.current) return;
    const pos=index===0?s.target:orbitPoint(s.time*(.035+index*.009)+index*1.8,2.55+index*.20,[-.5,.72,-.6,.3][index] ?? 0);
    ref.current.position.set(...pos);ref.current.rotation.set(.2,s.time*.03,.15);
    ref.current.visible=!(index===0 && s.phase==='collision');
    if(exhaust.current){exhaust.current.visible=index===0 && s.avoids && s.time>=10 && s.time<=13;exhaust.current.scale.setScalar(.8+.2*Math.sin(s.time*30));}
    if(halo.current){halo.current.visible=index===0 && s.time>7 && s.time<14;halo.current.scale.setScalar(1+.12*Math.sin(s.time*7));}
  });
  return <group ref={ref}>
    <mesh><boxGeometry args={[.13,.15,.14]}/><meshStandardMaterial color={p.metal} metalness={.7} roughness={.3}/></mesh>
    {[-1,1].map(side=><group key={side}><mesh position={[side*.21,0,0]}><boxGeometry args={[.25,.013,.15]}/><meshStandardMaterial color={p.solar} emissive={p.primary} emissiveIntensity={.12} metalness={.7} roughness={.3}/></mesh>{[0,1,2].map(i=><mesh key={i} position={[side*.21+(i-1)*.07,.009,0]}><boxGeometry args={[.004,.003,.15]}/><meshBasicMaterial color={p.metal}/></mesh>)}</group>)}
    <mesh position={[0,.11,0]} rotation-x={.7}><cylinderGeometry args={[.06,.02,.035,12]}/><meshStandardMaterial color={p.metal}/></mesh>
    <mesh ref={exhaust} position={[-.19,0,0]} rotation-z={-Math.PI/2}><coneGeometry args={[.065,.24,10]}/><meshBasicMaterial color={p.primary} transparent opacity={.8} blending={THREE.AdditiveBlending}/></mesh>
    <mesh ref={halo}><sphereGeometry args={[.27,16,12]}/><meshBasicMaterial color={p.warning} wireframe transparent opacity={.2}/></mesh>
    <ObjectLabel object={ref} name={names[index] ?? 'SATELLITE'} detail={`${index===0?'550':580+index*45} KM · LEO`}/>
  </group>;
}
function DebrisBody({ p }: {p:Palette}) {
  return <>
    <mesh><capsuleGeometry args={[.11,.14,5,12]}/><meshStandardMaterial color={p.destructive} emissive={p.destructive} emissiveIntensity={.2} metalness={.35} roughness={.38}/></mesh>
    <mesh position={[0,.05,.10]} scale={[1,.65,.45]}><sphereGeometry args={[.09,16,12]}/><meshStandardMaterial color={p.visor} metalness={.8} roughness={.12}/></mesh>
    <mesh position={[0,0,-.11]}><boxGeometry args={[.13,.18,.08]}/><meshStandardMaterial color={p.destructive}/></mesh>
    {[-1,1].map(side=><mesh key={side} position={[side*.06,-.15,0]}><capsuleGeometry args={[.046,.045,4,8]}/><meshStandardMaterial color={p.destructive}/></mesh>)}
  </>;
}
const extraDebris:{name:string;detail:string;phase:number;inclination:number;radius:number;scale:number}[]=[
  {name:'DEB-48302',detail:'560 KM · LEO',phase:.4,inclination:-.5,radius:3.1,scale:.5},
  {name:'DEB-48317',detail:'UNCONTROLLED',phase:1.9,inclination:.62,radius:3.35,scale:.55},
  {name:'DEB-48355',detail:'ROTATING',phase:3.6,inclination:-.15,radius:3.6,scale:.6},
];
function DebrisField({p}:{p:Palette}) {
  const main=useRef<THREE.Group>(null);
  const extras=[useRef<THREE.Group>(null),useRef<THREE.Group>(null),useRef<THREE.Group>(null)];
  useFrame(()=>{
    const s=useSimulation.getState().snapshot;
    if(main.current){main.current.position.set(...s.debris);main.current.rotation.set(s.time*.46,s.time*.31,s.time*.2);main.current.visible=s.phase!=='collision'&&s.phase!=='reset';}
    extras.forEach((r,i)=>{if(!r.current)return;const d=extraDebris[i]!;const ang=d.phase+s.time*(.045+i*.018);r.current.position.set(d.radius*Math.cos(ang),d.radius*Math.sin(ang)*Math.sin(d.inclination),d.radius*Math.sin(ang)*Math.cos(d.inclination));r.current.rotation.set(s.time*(.5+i*.14),s.time*(.32-i*.07),s.time*.25);r.current.visible=s.phase!=='collision'&&s.phase!=='reset';});
  });
  return <>
    <group ref={main} scale={.7}><DebrisBody p={p}/><ObjectLabel object={main} name="DEB-48219" detail="UNCONTROLLED" debris/></group>
    {extraDebris.map((d,i)=>(<group key={d.name} ref={extras[i]!} scale={d.scale}><DebrisBody p={p}/><ObjectLabel object={extras[i]!} name={d.name} detail={d.detail} debris/></group>))}
  </>;
}
function Effects({p}:{p:Palette}) {
  const particles=useRef<THREE.InstancedMesh>(null);const shock=useRef<THREE.Mesh>(null);
  const dummy=useMemo(()=>new THREE.Object3D(),[]);
  useFrame(()=>{const s=useSimulation.getState().snapshot;const impact=s.phase==='collision';
    if(particles.current){particles.current.visible=impact;for(let i=0;i<30;i++){const t=Math.max(0,s.time-14);const a=i*2.399;dummy.position.set(s.originalTarget[0]+Math.cos(a)*t*.35,s.originalTarget[1]+Math.sin(a)*t*.35,s.originalTarget[2]+Math.sin(i*7)*t*.3);dummy.scale.setScalar(Math.max(0,1-t/4)*.025);dummy.updateMatrix();particles.current.setMatrixAt(i,dummy.matrix);}particles.current.instanceMatrix.needsUpdate=true;}
    if(shock.current){shock.current.visible=impact;shock.current.position.set(...s.originalTarget);shock.current.scale.setScalar(.2+(s.time-14)*.8);(shock.current.material as THREE.MeshBasicMaterial).opacity=Math.max(0,.8-(s.time-14)*.4);}
  });
  return <><instancedMesh ref={particles} args={[undefined,undefined,30]}><sphereGeometry args={[1,6,4]}/><meshBasicMaterial color={p.warning}/></instancedMesh><mesh ref={shock}><torusGeometry args={[.3,.012,8,50]}/><meshBasicMaterial color={p.destructive} transparent blending={THREE.AdditiveBlending} depthWrite={false}/></mesh></>;
}
function World({p}:{p:Palette}) {
  const elapsed=useRef(4);const publish=useRef(0);const controls=useRef<Controls>(null);const revision=useSimulation(s=>s.viewRevision);const autoOrbit=useSimulation(s=>s.autoOrbit);const {camera}=useThree();
  useEffect(()=>{camera.position.set(0,9.6,1.6);if(controls.current){controls.current.target.set(0,0,0);controls.current.update();}},[revision,camera]);
  useFrame((_,raw)=>{
    const state=useSimulation.getState();const dt=Math.min(raw,.05);
    if(state.playing){elapsed.current+=dt*state.speed;publish.current+=dt;
      if(publish.current>.08){const snapshot=sampleSimulation(elapsed.current,state.mode);useSimulation.setState({snapshot,elapsed:elapsed.current});publish.current=0;}
    }
  },-1);
  const stars=useMemo(()=>{const positions=new Float32Array(700*3);for(let i=0;i<700;i++){const a=i*2.399;const y=((i*73)%701)/350-1;const r=28;positions[i*3]=Math.cos(a)*Math.sqrt(1-y*y)*r;positions[i*3+1]=y*r;positions[i*3+2]=Math.sin(a)*Math.sqrt(1-y*y)*r;}return positions;},[]);
  const ring=useMemo(()=>Array.from({length:161},(_,j)=>[2.85*Math.cos(j/160*Math.PI*2),.7*Math.sin(j/160*Math.PI*2),2.7*Math.sin(j/160*Math.PI*2)] as Vec3),[]);
  const s=useSimulation(state=>state.snapshot);
  const encounter:Vec3=[2.85*Math.cos(.73),.7*Math.sin(.73),2.7*Math.sin(.73)];
  const trajectory:Vec3[]=[[encounter[0]+3.2,encounter[1]+2,encounter[2]+1.3],encounter,[encounter[0]-1.4,encounter[1]-.9,encounter[2]-.6]];
  return <>
    <ambientLight intensity={.7}/><directionalLight position={[-4,6,6]} intensity={2}/>
    <Environment resolution={64}><Lightformer intensity={2} position={[0,5,0]} scale={[10,10,1]} color={p.cloud}/><Lightformer intensity={1} position={[-5,0,1]} rotation-y={Math.PI/2} scale={[10,4,1]} color={p.primary}/></Environment>
    <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[stars,3]}/></bufferGeometry><pointsMaterial color={p.cloud} size={.035} transparent opacity={.6} sizeAttenuation/></points>
    <Earth p={p}/>
    <Line points={ring} color={p.primary} lineWidth={1.1} transparent opacity={.65}/>
    <Line points={trajectory} color={p.destructive} dashed dashSize={.10} gapSize={.07} lineWidth={1} transparent opacity={.6}/>
    {s.time>8 && s.avoids && <Line points={[encounter,[encounter[0]+.52,encounter[1]+.25,encounter[2]],[2.9,1.1,2.8]]} color={p.primary} lineWidth={1.5} transparent opacity={.85}/>}
    <Satellite index={0} p={p}/><DebrisField p={p}/><Effects p={p}/>
    <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={.06} enablePan={false} minDistance={5.5} maxDistance={14} autoRotate={autoOrbit && useSimulation.getState().playing} autoRotateSpeed={.15}/>
  </>;
}
export function OrbitalScene() {
  const [palette,setPalette]=useState<Palette|null>(null);
  useEffect(()=>setPalette(readPalette()),[]);
  return palette?<Canvas dpr={[1,1.5]} camera={{position:[0,9.6,1.6],fov:45}} gl={{antialias:true,alpha:true}}><World p={palette}/></Canvas>:null;
}
