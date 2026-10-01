import {AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Video,Audio} from '@remotion/media';
import {Props,Scene} from './schema';
import {QuestionHook} from './components/QuestionHook';
import {AnimatedMessages} from './components/AnimatedMessages';
import {CRMHighlight} from './components/CRMHighlight';
import {StepDiagram} from './components/StepDiagram';
import {ScreenshotFocus} from './components/ScreenshotFocus';
import {SummaryCTA} from './components/SummaryCTA';
import {Captions} from './components/Captions';

const components={QuestionHook,AnimatedMessages,CRMHighlight,StepDiagram,ScreenshotFocus,SummaryCTA};
function SceneView({scene}:{scene:Scene}){
  // Un asset autorizado siempre conserva su contenido, aunque se solicite CRMHighlight.
  const Component=scene.kind==='asset'?ScreenshotFocus:components[scene.template];
  return <Component scene={scene}/>;
}
export const DentFlow=(p:Props)=>{
  const frame=useCurrentFrame();const {width,fps}=useVideoConfig();
  const reframe=p.scenes.find(s=>s.kind==='reframe'&&s.start_frame<=frame&&frame<s.start_frame+s.duration_frames);
  const camera=reframe?.camera;
  const zoom=camera?(camera.animated?1+(camera.scale-1)*Math.sin(Math.PI*(frame-reframe!.start_frame)/reframe!.duration_frames)**2:camera.scale):1;
  return <AbsoluteFill style={{background:'#071629',overflow:'hidden'}}>
    <div style={{position:'absolute',width:1080,height:1920,transform:`scale(${width/1080})`,transformOrigin:'top left',fontFamily:'Arial, sans-serif'}}>
      {p.base_video&&<Video src={staticFile(p.base_video)} style={{position:'absolute',width:1080,height:1920,objectFit:'contain',
        scale:String(zoom),transformOrigin:`${(camera?.x??.5)*100}% ${(camera?.y??.5)*100}%`}}/>}
      {p.scenes.filter(s=>s.kind!=='reframe').map(s=><Sequence key={s.id} from={s.start_frame} durationInFrames={s.duration_frames} name={s.id}>
        <SceneView scene={s}/>
      </Sequence>)}
      <Captions captions={p.captions} fontSize={p.subtitle_style.font_size} margin={p.subtitle_style.margin_v}/>
      {p.music&&<Audio src={staticFile(p.music.path)} volume={f=>{
        const seconds=f/fps;
        const speech=p.speech_windows.reduce((level,[a,b])=>Math.max(level,
          Math.max(0,Math.min(1,(seconds-(a-.2))/.2,((b+.35)-seconds)/.35))),0);
        const fade=Math.max(0,Math.min(1,f/fps,(p.duration_frames-1-f)/fps));
        return p.music!.volume*(1-speech*(1-p.music!.ducking))*fade;
      }}/>}
    </div>
  </AbsoluteFill>;
};
