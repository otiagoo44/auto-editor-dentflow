import {Scene} from '../schema';
import {SceneFrame,Cards} from './Design';
export const StepDiagram=({scene}:{scene:Scene})=><SceneFrame scene={scene}><Cards scene={scene} numbered/></SceneFrame>;
