import {Scene} from '../schema';
import {SceneFrame,Cards} from './Design';
export const CRMHighlight=({scene}:{scene:Scene})=><SceneFrame scene={scene}><Cards scene={scene}/></SceneFrame>;
