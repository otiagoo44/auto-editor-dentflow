import {Composition,CalculateMetadataFunction} from 'remotion';
import {DentFlow} from './Composition';
import {Props,propsSchema} from './schema';
const defaults:Props={format_version:1,job_id:'job_studio',template:'comercial',fps:30,width:1080,height:1920,duration_frames:150,
  base_video:null,captions:[],speech_windows:[],subtitle_style:{font_size:54,margin_v:270},music:null,
  metadata:{source_sha256:'',source_type:'studio_example'},scenes:[{id:'ejemplo',kind:'motion',template:'StepDiagram',start_frame:0,duration_frames:150,
    layout:'full',demo:true,animation:'fade',params:{title:'Cada consulta.\nUn siguiente paso.',theme:'dark',items:[
      {label:'01 / ESTADO',value:'Seguimiento pendiente',at_seconds:0},
      {label:'02 / RESPONSABLE',value:'Recepción',at_seconds:.6},
      {label:'03 / PRÓXIMA ACCIÓN',value:'Revisar hoy',at_seconds:1.2}]}}]};
const metadata:CalculateMetadataFunction<Props>=({props})=>{
  const p=propsSchema.parse(props);
  return {durationInFrames:p.duration_frames,fps:p.fps,width:p.width,height:p.height,props:p};
};
export const Root=()=><>
  <Composition id="DentFlowEducativo" component={DentFlow} defaultProps={{...defaults,template:'educativo'}} calculateMetadata={metadata} durationInFrames={150} fps={30} width={1080} height={1920}/>
  <Composition id="DentFlowComercial" component={DentFlow} defaultProps={defaults} calculateMetadata={metadata} durationInFrames={150} fps={30} width={1080} height={1920}/>
</>;
