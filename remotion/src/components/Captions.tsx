import type {Caption} from '@remotion/captions';
import {useCurrentFrame,useVideoConfig} from 'remotion';
export const Captions=({captions,fontSize,margin}:{captions:Caption[];fontSize:number;margin:number})=>{
  const f=useCurrentFrame();const {fps}=useVideoConfig();
  const c=captions.find(x=>f>=Math.floor(x.startMs*fps/1000+.5)&&f<Math.floor(x.endMs*fps/1000+.5));
  if(!c) return null;
  return <div style={{position:'absolute',left:80,right:90,bottom:margin,textAlign:'center',fontSize,fontWeight:700,lineHeight:1.22,color:'white',
    textShadow:'0 2px 4px #000, 2px 0 3px #000, -2px 0 3px #000',whiteSpace:'pre-line'}}>
    <span style={{background:'rgba(7,22,41,.87)',borderRadius:10,padding:'8px 18px',boxDecorationBreak:'clone'}}>{c.text}</span>
  </div>;
};
