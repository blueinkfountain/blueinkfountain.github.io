import {solveLab} from './solver.mjs?v=time-budget-v1';
self.onmessage=({data})=>{
  try{self.postMessage(solveLab(data));}
  catch(error){self.postMessage({error:error.message});}
};
