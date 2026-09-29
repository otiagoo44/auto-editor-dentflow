import {Scene} from '../schema';
import {SceneFrame,Reveal,palette} from './Design';
export const SummaryCTA=({scene}:{scene:Scene})=><SceneFrame scene={scene}>
  {scene.params.cta&&<div style={{position:'absolute',top:1000,left:84,right:100}}><Reveal>
    <div style={{padding:'38px 42px',background:palette.blue,borderRadius:22,color:palette.navy,fontSize:52,fontWeight:750,lineHeight:1.2}}>{scene.params.cta}</div>
  </Reveal></div>}
</SceneFrame>;
