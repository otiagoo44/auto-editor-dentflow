import {Scene} from '../schema';
import {SceneFrame,Reveal,palette} from './Design';
export const AnimatedMessages=({scene}:{scene:Scene})=><SceneFrame scene={scene}>
  <div style={{position:'absolute',left:84,right:100,top:scene.layout==='full'?700:570,display:'flex',flexDirection:'column',gap:18}}>
    {scene.params.items.map((item,i)=><Reveal key={i} at={item.at_seconds}>
      <div style={{marginLeft:i%2?95:0,marginRight:i%2?0:95,background:i%2?'#245886':'#142E48',border:`2px solid ${i%2?'#4684B4':'#35536F'}`,
        borderRadius:i%2?'24px 24px 6px 24px':'24px 24px 24px 6px',padding:'18px 25px',color:'white'}}>
        <div style={{fontSize:25,color:palette.muted,marginBottom:6,letterSpacing:.5}}>{item.label}</div>
        <div style={{fontSize:item.value.length>50?30:36,lineHeight:1.18,overflowWrap:'anywhere'}}>{item.value}</div>
      </div>
    </Reveal>)}
  </div>
</SceneFrame>;
