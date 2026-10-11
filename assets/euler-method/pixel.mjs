/**
 * Small pure helpers for a deliberately un-antialiased, SFML-like plot.
 * The numerical solutions stay unchanged; only plotting is pixel-rasterized.
 */

// Liang–Barsky clip against a rectangle. Return [x0,y0,x1,y1] or null.
export function clipSegment(x0,y0,x1,y1,xmin,ymin,xmax,ymax) {
  if (![x0,y0,x1,y1,xmin,ymin,xmax,ymax].every(Number.isFinite)) return null;
  const dx=x1-x0, dy=y1-y0;
  let lo=0, hi=1;
  const edges=[[-dx,x0-xmin],[dx,xmax-x0],[-dy,y0-ymin],[dy,ymax-y0]];
  for(const [p,q] of edges){
    if(p===0){if(q<0)return null;continue;}
    const t=q/p;
    if(p<0){if(t>hi)return null;lo=Math.max(lo,t);}
    else {if(t<lo)return null;hi=Math.min(hi,t);}
  }
  return [x0+lo*dx,y0+lo*dy,x0+hi*dx,y0+hi*dy];
}

/** Emits exact integer pixel cells along a 1-pixel-wide Bresenham line. */
export function rasterLine(x0,y0,x1,y1,plot){
  x0=Math.round(x0);y0=Math.round(y0);
  x1=Math.round(x1);y1=Math.round(y1);
  if(![x0,y0,x1,y1].every(Number.isFinite))return;
  const dx=Math.abs(x1-x0),dy=Math.abs(y1-y0);
  const sx=x0<x1?1:-1,sy=y0<y1?1:-1;
  let err=dx-dy;
  for(let i=0;i<=Math.max(dx,dy);i++){
    plot(x0,y0,i);
    if(x0===x1&&y0===y1)break;
    const e2=2*err;
    if(e2>-dy){err-=dy;x0+=sx;}
    if(e2<dx){err+=dx;y0+=sy;}
  }
}

/**
 * Drawable pixel-canvas painter. Input coordinates are CSS plot pixels;
 * output is discrete cells of size `pixelSize` CSS pixels. Every segment is
 * clipped before rasterization, preventing huge loops on diverging ODEs.
 */
export class PixelPainter {
  constructor(ctx, width, height, pixelSize) {
    this.ctx=ctx;
    this.width=width;
    this.height=height;
    this.pixelSize=pixelSize;
    this.pixelWidth=ctx.canvas.width;
    this.pixelHeight=ctx.canvas.height;
  }
  line(x0,y0,x1,y1,color,dash=0){
    const clipped=clipSegment(
      x0/this.pixelSize,y0/this.pixelSize,
      x1/this.pixelSize,y1/this.pixelSize,
      0,0,this.pixelWidth-1,this.pixelHeight-1
    );
    if(!clipped)return;
    const g=this.ctx;
    g.fillStyle=color;
    const stride=dash>0?Math.max(3,Math.round(dash/this.pixelSize)):0;
    rasterLine(...clipped,(x,y,i)=>{
      if(!stride||(i%(stride*2))<stride)g.fillRect(x,y,1,1);
    });
  }
  point(x,y,color,radius=1){
    const ix=Math.round(x/this.pixelSize),iy=Math.round(y/this.pixelSize);
    if(ix < -radius || iy < -radius || ix > this.pixelWidth+radius || iy > this.pixelHeight+radius)return;
    this.ctx.fillStyle=color;
    this.ctx.fillRect(ix-radius,iy-radius,2*radius+1,2*radius+1);
  }
}
