/** Restricted, offline LaTeX expression parser for f(x,y), x(t), and y(t).
 * Never calls eval / Function / external network. Input length, token count,
 * nesting and exponent magnitude are limited to keep graph updates responsive.
 */
const FUNCS = Object.freeze({
  sin: Math.sin, cos: Math.cos, tan: Math.tan,
  asin: Math.asin, acos: Math.acos, atan: Math.atan,
  sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh,
  exp: Math.exp, ln: Math.log, log: Math.log10,
  sqrt: Math.sqrt, abs: Math.abs, floor: Math.floor, ceil: Math.ceil,
});
const CONSTANTS = Object.freeze({pi: Math.PI, e: Math.E});

function normalise(s) {
  return s.trim()
    .replace(/\\left\s*/g, '').replace(/\\right\s*/g, '')
    .replace(/\\operatorname\s*\{\s*([a-zA-Z]+)\s*\}/g, '$1')
    .replace(/\\mathrm\s*\{\s*e\s*\}/g, 'e')
    .replace(/[−–]/g, '-')
    .replace(/[×·⋅]/g, '*')
    .replace(/\\(?:cdot|times)\b/g, '*')
    .replace(/\\,/g, '').replace(/\\;/g, '')
    .replace(/\\!/g, '')
    .replace(/π/g, 'pi')
    .replace(/²/g, '^2').replace(/³/g, '^3')
    .replace(/\s+/g, '');
}

function stripLhs(s) {
  const equal = s.indexOf('=');
  if (equal < 0) return s;
  const lhs = s.slice(0, equal).toLowerCase();
  if (/^(?:y''|y′′|y′'|y'′|\\frac\{d\^2y\}\{dx\^2\}|\\dfrac\{d\^2y\}\{dx\^2\}|y'|y′|f\(x,y\)|\\frac\{dy\}\{dx\}|\\dfrac\{dy\}\{dx\}|\\dot\{y\}|x\(t\)|y\(t\))$/.test(lhs)) {
    return s.slice(equal + 1);
  }
  throw new SyntaxError('Enter an expression or an equation with y′, f(x,y), x(t), or y(t) on the left.');
}

function tokenize(text) {
  const tokens=[];
  for(let i=0;i<text.length;){
    if(tokens.length>300) throw new SyntaxError('Formula is too long.');
    const c=text[i];
    if('+-*/^(){}[]|'.includes(c)){tokens.push(c);i++;continue;}
    if(c==='\\'){
      const m=/^\\([a-zA-Z]+)/.exec(text.slice(i));
      if(!m) throw new SyntaxError('Invalid LaTeX command near character '+(i+1));
      const command=m[1];
      if(!['frac','dfrac','sqrt',...Object.keys(FUNCS),'pi'].includes(command))throw new SyntaxError('Unsupported LaTeX command \\'+command);
      tokens.push(command==='dfrac'?'frac':command);i+=m[0].length;continue;
    }
    if(/[0-9.]/.test(c)){
      const m=/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(text.slice(i));
      if(!m)throw new SyntaxError('Invalid number at character '+(i+1));
      tokens.push(Number(m[0]));i+=m[0].length;continue;
    }
    if(/[a-zA-Z]/.test(c)){
      const rem=text.slice(i);
      const words=['floor','sinh','cosh','tanh','asin','acos','atan','sqrt','ceil','sin','cos','tan','exp','log','abs','ln','pi'];
      const found=words.find(x=>rem.startsWith(x));
      if(found){tokens.push(found);i+=found.length;continue;}
      if('xytev'.includes(c)){tokens.push(c);i++;continue;}
      throw new SyntaxError('Unknown symbol '+c+'. Use x, y, t, numbers or supported functions.');
    }
    throw new SyntaxError('Unexpected character '+c+' at position '+(i+1));
  }
  tokens.push('<end>');
  return tokens;
}

export function compileLatex(input, variables=['x','y']) {
  if(typeof input !== 'string' || !input.trim())throw new SyntaxError('Formula cannot be empty.');
  if(input.length>300)throw new SyntaxError('Formula must be 300 characters or fewer.');
  const allowed = new Set(variables);
  let expression=stripLhs(normalise(input));
  if(allowed.has('v')){
    // In a second-order ODE, v means y'. Allow familiar derivative notation.
    expression=expression
      .replace(/\\(?:frac|dfrac)\{dy\}\{dx\}/g,'v')
      .replace(/y['′]/g,'v');
  }
  const tokens=tokenize(expression);
  let i=0, depth=0;
  const peek=()=>tokens[i];
  const take=()=>tokens[i++];
  const expect=t=>{if(take()!==t)throw new SyntaxError('Expected '+t+'. Check parentheses and braces.');};
  const descend=fn=>{if(++depth>60)throw new SyntaxError('Formula is nested too deeply.');try{return fn();}finally{depth--;}};
  const isStart=t=>typeof t==='number' || typeof t==='string' && (
    t==='('||t==='{'||t==='sqrt'||t==='frac'||t in FUNCS||t==='pi'||'xytev'.includes(t)&&t.length===1
  );
  function grouped(){
    const opener=peek();
    if(!['{','(','['].includes(opener))throw new SyntaxError('Expected a grouped expression in braces.');
    take();const inner=expr();expect(opener==='{'?'}':opener==='('?')':']');return inner;
  }
  function argument(){
    if(['{','('].includes(peek())) return grouped();
    return unary();
  }
  function primary(){return descend(()=>{
    const t=peek();
    if(typeof t==='number'){take();return ()=>t;}
    if(t==='('||t==='{')return grouped();
    if(t==='|'){take();const f=expr();expect('|');return v=>Math.abs(f(v));}
    if(t==='frac'){
      take();const a=grouped(),b=grouped();return v=>a(v)/b(v);
    }
    if(t==='sqrt'){
      take();let root=null;
      if(peek()==='[')root=grouped();
      const f=argument();
      return root?(v)=>Math.pow(f(v),1/root(v)):(v)=>Math.sqrt(f(v));
    }
    if(t in FUNCS){
      take();
      let power=null;
      if(peek()==='^'){take();power=unary();}
      const f=argument(),apply=FUNCS[t];
      return power?(v)=>Math.pow(apply(f(v)),power(v)):(v)=>apply(f(v));
    }
    if(t==='pi'||t==='e'){take();return ()=>CONSTANTS[t];}
    if(typeof t==='string' && /^[xytv]$/.test(t)){
      if(!allowed.has(t))throw new SyntaxError('The variable '+t+' is not valid in this formula.');
      take();return v=>v[t];
    }
    throw new SyntaxError('Unexpected token '+t+'. Check the formula syntax.');
  });}
  function power(){
    const a=primary();
    if(peek()==='^'){take();const b=unary();return v=>Math.pow(a(v),b(v));}
    return a;
  }
  function unary(){
    if(peek()==='+'){take();return unary();}
    if(peek()==='-'){take();const f=unary();return v=>-f(v);}
    return power();
  }
  function product(){
    let left=unary();
    while(peek()==='*'||peek()==='/'||isStart(peek())){
      const op=peek();
      if(op==='*'||op==='/')take();
      const right=unary(), prior=left;
      left=op==='/'?(v)=>prior(v)/right(v):(v)=>prior(v)*right(v);
    }
    return left;
  }
  function expr(){return descend(()=>{
    let left=product();
    while(peek()==='+'||peek()==='-'){
      const op=take(),right=product(),prior=left;
      left=op==='+'?(v)=>prior(v)+right(v):(v)=>prior(v)-right(v);
    }
    return left;
  });}
  const f=expr();
  if(peek()!=='<end>')throw new SyntaxError('Unexpected token '+peek()+'. Check the expression.');
  return (...args)=>{
    const scope={};variables.forEach((v,k)=>{scope[v]=args[k];});
    const result=f(scope);
    return Number.isFinite(result) ? result : NaN;
  };
}
