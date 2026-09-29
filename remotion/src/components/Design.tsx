import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Scene} from '../schema';

export const palette={navy:'#071629',blue:'#5EA9FA',ink:'#10263F',light:'#F1F6FA',muted:'#ADC2D6'};
export const entrance=(f:number,fps:number)=>spring({frame:Math.max(0,f),fps,config:{damping:24,stiffness:110,mass:.7}});

export const Reveal:React.FC<{at?:number;children:React.ReactNode}>=({at=0,children})=>{
  const frame=useCurrentFrame(); const {fps}=useVideoConfig();
  const local=frame-at*fps;
  return <div style={{opacity:interpolate(local,[0,9],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),
    translate:`0 ${interpolate(entrance(local,fps),[0,1],[28,0])}px`}}>{children}</div>;
};

export const SceneFrame:React.FC<{scene:Scene;children?:React.ReactNode}>=({scene,children})=>{
  const light=scene.params.theme==='light'; const full=scene.layout==='full';
  return <AbsoluteFill style={{background:full?(light?palette.light:palette.navy):'transparent',color:light?palette.ink:'white'}}>
    {full&&<>
      <div style={{position:'absolute',top:0,right:0,width:500,height:700,borderBottomLeftRadius:500,background:light?'#E6EFF8':'#0C2442'}}/>
      <div style={{position:'absolute',left:84,top:145,fontSize:32,letterSpacing:3,fontWeight:700,color:light?'#366EAB':palette.muted}}>DENTFLOW <span style={{color:palette.blue}}> / </span> {scene.params.eyebrow||'UNA IDEA, UN SIGUIENTE PASO'}</div>
    </>}
    <div style={{position:'absolute',left:84,right:100,top:full?286:240}}>
      {scene.params.title&&<Reveal><div style={{fontSize:scene.params.title.length>62?76:88,fontWeight:750,lineHeight:1.08,letterSpacing:-2.5,
        background:full?'transparent':'rgba(7,22,41,.94)',borderRadius:22,padding:full?0:'30px 36px',whiteSpace:'pre-line'}}>{scene.params.title}</div></Reveal>}
      {full&&scene.params.subtitle&&<Reveal><div style={{fontSize:44,lineHeight:1.3,color:light?'#48637C':palette.muted,marginTop:28}}>{scene.params.subtitle}</div></Reveal>}
    </div>
    {children}
    {scene.demo&&<div style={{position:'absolute',left:84,right:84,top:1330,fontSize:32,fontWeight:650,color:light?'#365673':'#C8DDEF',
      background:full?'transparent':palette.navy,padding:'12px 0',letterSpacing:1}}>EJEMPLO FICTICIO · DATOS ILUSTRATIVOS</div>}
  </AbsoluteFill>;
};

export const Cards:React.FC<{scene:Scene;numbered?:boolean}>=({scene,numbered=false})=>{
  const light=scene.params.theme==='light';
  return <div style={{position:'absolute',left:84,right:100,top:scene.layout==='full'?640:520,display:'flex',flexDirection:'column',gap:20}}>
    {scene.params.items.map((item,i)=><Reveal key={i} at={item.at_seconds}>
      <div style={{padding:'24px 30px',borderRadius:22,background:light?'white':'#112D49',border:`2px solid ${light?'#DAE6F0':'#234764'}`,
        boxShadow:'0 7px 0 rgba(0,0,0,.06)',display:'flex',gap:24,alignItems:'center'}}>
        {numbered&&<div style={{fontSize:40,color:light?'#317DC4':palette.blue,fontWeight:700,minWidth:58}}>{String(i+1).padStart(2,'0')}</div>}
        <div style={{minWidth:0}}><div style={{fontSize:item.value?32:46,fontWeight:700,lineHeight:1.2,color:item.value?(light?'#4C6A83':palette.muted):undefined}}>{item.label}</div>
        {item.value&&<div style={{fontSize:46,lineHeight:1.15,fontWeight:650,marginTop:8}}>{item.value}</div>}</div>
      </div>
    </Reveal>)}
  </div>;
};
