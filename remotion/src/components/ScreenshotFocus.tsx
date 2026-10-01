import {Img, staticFile, useCurrentFrame, interpolate} from 'remotion';
import {Video} from '@remotion/media';
import {Scene} from '../schema';
import {SceneFrame} from './Design';
export const ScreenshotFocus=({scene}:{scene:Scene})=>{
  const frame=useCurrentFrame();
  const opacity=scene.animation==='none'?1:interpolate(frame,[0,Math.min(5,scene.duration_frames/4)],[0,1],{extrapolateRight:'clamp'});
  // A subtle settling movement preserves all pixels of the already authorized crop.
  const scale=scene.animation==='none'?1:interpolate(frame,[0,Math.min(30,scene.duration_frames/3)],[.96,1],{extrapolateRight:'clamp'});
  const style={width:'100%',height:'100%',objectFit:'contain' as const,scale:String(scale)};
  return <SceneFrame scene={scene}>
    <div style={{position:'absolute',left:72,right:84,top:scene.params.title?590:350,height:scene.params.title?680:920,
      borderRadius:24,overflow:'hidden',background:'#11263E',opacity,border:'2px solid #234764'}}>
      {scene.asset?.video?<Video src={staticFile(scene.asset.path)} muted style={style}/>:scene.asset&&<Img src={staticFile(scene.asset.path)} style={style}/>}
    </div>
  </SceneFrame>;
};
