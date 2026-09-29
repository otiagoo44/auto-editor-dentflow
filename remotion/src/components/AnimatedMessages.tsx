import {Scene} from '../schema';
import {SceneFrame,Cards} from './Design';
export const AnimatedMessages=({scene}:{scene:Scene})=><SceneFrame scene={scene}><Cards scene={scene}/></SceneFrame>;
