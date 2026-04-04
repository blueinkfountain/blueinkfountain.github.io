---
layout: default
title: Brouwer fixed point theorem
parent: Simulations
nav_order: 2
---

#

---
<div id="brouwer-wrapper" style="margin: 20px 0;">
    <style>
        #simulation-container {
            text-align: center;
            background: #ffffff;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 15px;
        }
        #brouwerCanvas {
            background: #fff;
            border: 2px solid #333;
            border-radius: 50%; /* 디스크 모양 */
            cursor: crosshair;
            touch-action: none;
            max-width: 100%;
            height: auto;
        }
        .controls { margin-top: 15px; }
        .controls button {
            padding: 10px 20px;
            font-size: 14px;
            cursor: pointer;
            background: #4A90E2;
            color: white;
            border: none;
            border-radius: 5px;
            margin: 0 5px;
        }
    </style>

    <div id="simulation-container">
        <canvas id="brouwerCanvas" width="400" height="400"></canvas>
        <div class="controls">
            <button id="resetBtn">초기화</button>
            <button id="toggleBtn">고정점 확인</button>
        </div>
        <div id="info-text" style="margin-top:10px; font-size: 0.9em; color: #555;">
            마우스로 점들을 휘저은 뒤 버튼을 눌러보세요.
        </div>
    </div>

    <script type="text/javascript">
    (function() {
        window.addEventListener('load', function() {
            const canvas = document.getElementById('brouwerCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const radius = canvas.width / 2;
            const centerX = radius;
            const centerY = radius;
            
            let points = [];
            const numPoints = 600; 
            let showFixedPoint = false;

            class Point {
                constructor() {
                    let r = Math.sqrt(Math.random()) * (radius - 10);
                    let theta = Math.random() * 2 * Math.PI;
                    this.originX = centerX + r * Math.cos(theta);
                    this.originY = centerY + r * Math.sin(theta);
                    this.x = this.originX;
                    this.y = this.originY;
                    this.color = 'hsl(' + (Math.random() * 360) + ', 70%, 60%)';
                }
                draw() {
                    ctx.beginPath();
                    ctx.arc(this.x, this.y, 3, 0, Math.PI * 2);
                    ctx.fillStyle = this.color;
                    ctx.fill();
                }
                update(mX, mY, isDown) {
                    if (isDown) {
                        let dx = mX - this.x;
                        let dy = mY - this.y;
                        let dist = Math.sqrt(dx * dx + dy * dy);
                        if (dist < 50) {
                            this.x += dx * 0.15;
                            this.y += dy * 0.15;
                            let dfc = Math.sqrt(Math.pow(this.x - centerX, 2) + Math.pow(this.y - centerY, 2));
                            if (dfc > radius - 5) {
                                let angle = Math.atan2(this.y - centerY, this.x - centerX);
                                this.x = centerX + (radius - 5) * Math.cos(angle);
                                this.y = centerY + (radius - 5) * Math.sin(angle);
                            }
                        }
                    }
                }
            }

            function init() {
                points = [];
                for (let i = 0; i < numPoints; i++) { points.push(new Point()); }
            }

            let isMouseDown = false;
            let mouseX = 0, mouseY = 0;

            canvas.addEventListener('mousedown', () => isMouseDown = true);
            window.addEventListener('mouseup', () => isMouseDown = false);
            canvas.addEventListener('mousemove', (e) => {
                const rect = canvas.getBoundingClientRect();
                mouseX = e.clientX - rect.left;
                mouseY = e.clientY - rect.top;
            });

            document.getElementById('resetBtn').onclick = function() {
                init();
                showFixedPoint = false;
            };
            document.getElementById('toggleBtn').onclick = function() {
                showFixedPoint = !showFixedPoint;
            };

            function animate() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                let minD = Infinity;
                let fp = null;

                for (let p of points) {
                    p.update(mouseX, mouseY, isMouseDown);
                    p.draw();
                    let d = Math.sqrt(Math.pow(p.x - p.originX, 2) + Math.pow(p.y - p.originY, 2));
                    if (d < minD) { minD = d; fp = p; }
                }

                if (showFixedPoint && fp) {
                    ctx.beginPath();
                    ctx.arc(fp.x, fp.y, 12, 0, Math.PI * 2);
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                    ctx.fillStyle = 'red';
                    ctx.fillText("Fixed Point", fp.x + 15, fp.y);
                }
                requestAnimationFrame(animate);
            }

            init();
            animate();
        });
    })();
    </script>
</div>