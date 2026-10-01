import {Scene} from '../schema';
import {useCurrentFrame,useVideoConfig} from 'remotion';
import {SceneFrame,Reveal,palette} from './Design';
export const StepDiagram=({scene}:{scene:Scene})=>{
  const frame=useCurrentFrame();const {fps}=useVideoConfig();
  return <SceneFrame scene={scene}><div style={{position:'absolute',left:94,right:110,top:scene.layout==='full'?710:550}}>
    {scene.params.items.map((item,i)=><Reveal key={i} at={item.at_seconds}><div style={{display:'flex',gap:27,minHeight:137,color:scene.params.theme==='light'?palette.ink:'white'}}>
      <div style={{position:'relative',width:60,flexShrink:0}}><div style={{borderRadius:'50%',height:60,width:60,display:'grid',placeItems:'center',fontSize:30,fontWeight:700,background:palette.blue,color:palette.navy}}>{i+1}</div>
      {i<scene.params.items.length-1&&<div style={{position:'absolute',left:28,top:65,height:64,width:4,background:frame>=scene.params.items[i+1].at_seconds*fps?palette.blue:'#36506B'}}/>}</div>
      <div style={{paddingBottom:20}}><div style={{fontSize:30,color:scene.params.theme==='light'?'#436886':palette.muted}}>{item.label}</div><div style={{fontSize:item.value.length>48?32:39,lineHeight:1.15,fontWeight:700,marginTop:7,overflowWrap:'anywhere'}}>{item.value}</div></div>
    </div></Reveal>)}
  </div></SceneFrame>;
};
