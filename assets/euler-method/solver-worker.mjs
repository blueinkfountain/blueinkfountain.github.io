import {solveLab} from './solver.mjs';
self.onmessage=({data})=>{
  try{self.postMessage(solveLab(data));}
  catch(error){self.postMessage({error:error.message});}
};
