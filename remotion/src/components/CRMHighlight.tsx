import {Scene} from '../schema';
import {useCurrentFrame,useVideoConfig} from 'remotion';
import {SceneFrame,Reveal,palette} from './Design';
export const CRMHighlight=({scene}:{scene:Scene})=>{
  const frame=useCurrentFrame();const {fps}=useVideoConfig();
  const selected=scene.params.items.reduce((index,item,i)=>frame>=item.at_seconds*fps?i:index,-1);
  return <SceneFrame scene={scene}><div style={{position:'absolute',left:84,right:100,top:scene.layout==='full'?690:560,
    borderRadius:24,overflow:'hidden',background:'#F1F6FA',border:'2px solid #8BAAC4',color:palette.ink}}>
    <div style={{padding:'22px 28px',background:'#DDEAF4',display:'flex',justifyContent:'space-between',fontSize:24,letterSpacing:1.5,fontWeight:700}}>
      <span>FICHA ILUSTRATIVA</span><span style={{color:'#37658B'}}>EJEMPLO</span></div>
    {scene.params.items.map((item,i)=><Reveal key={i} at={item.at_seconds}><div style={{padding:'20px 28px',display:'grid',gridTemplateColumns:'245px 1fr',gap:20,
      borderTop:'1px solid #C8D9E7',borderLeft:`7px solid ${i===selected?palette.blue:'transparent'}`,background:i===selected?'#D7EAFB':'#F1F6FA'}}>
      <div style={{fontSize:28,color:'#456780',lineHeight:1.2}}>{item.label}</div><div style={{fontSize:item.value.length>48?29:34,fontWeight:700,lineHeight:1.2,overflowWrap:'anywhere'}}>{item.value}</div>
    </div></Reveal>)}
  </div></SceneFrame>;
};
