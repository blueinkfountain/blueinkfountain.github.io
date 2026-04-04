---
layout: default
title: Brouwer fixed point theorem
parent: Simulations
nav_order: 2
---

#

<div id="brouwer-pro-wrapper" style="margin: 20px 0; font-family: sans-serif;">
    <style>
        #simulation-box {
            text-align: center;
            background: #fff;
            padding: 20px;
            border: 1px solid #eee;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        }
        canvas {
            border: 1px solid #333;
            border-radius: 50%;
            cursor: crosshair;
            background: #fafafa;
            touch-action: none;
        }
        .desc { font-size: 0.9em; color: #666; margin-bottom: 15px; line-height: 1.6; }
        .controls { margin-top: 15px; }
        button {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            background: #222;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
        }
        button:hover { background: #555; }
        #fixed-toggle.active { background: #ff4757; }
    </style>

    <div id="simulation-box">
        <h3 style="margin-top:0;">브라우어 고정점 정리 시뮬레이션</h3>
        <p class="desc">
            원반(디스크) 모양의 고무판을 마우스로 문질러 왜곡시켜보세요.<br>
            아무리 복잡하게 비틀어도, <b>원래 위치와 똑같은 위치</b>에 머무는 점이 반드시 존재합니다.
        </p>
        <canvas id="brouwerCanvas" width="400" height="400"></canvas>
        <div class="controls">
            <button id="resetBtn">공간 초기화</button>
            <button id="fixed-toggle">고정점(f(x)=x) 찾기</button>
        </div>
    </div>

    <script>
    (function() {
        const canvas = document.getElementById('brouwerCanvas');
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const radius = width / 2;
        
        let showFixed = false;
        let isDrawing = false;

        // 1. 격자 데이터 생성 (공간의 각 점이 어디로 이동했는지 저장)
        // grid[i][j]는 초기 위치 (x,y)가 현재 어디(tx, ty)에 있는지를 저장함
        const resolution = 20; 
        let points = [];

        function initGrid() {
            points = [];
            for (let y = 0; y <= width; y += resolution) {
                for (let x = 0; x <= width; x += resolution) {
                    // 디스크 내부 점들만 생성
                    if (Math.sqrt((x-radius)**2 + (y-radius)**2) < radius) {
                        points.push({
                            ox: x, oy: y, // Original position (고정값)
                            x: x,  y: y   // Transformed position (변화값)
                        });
                    }
                }
            }
        }

        // 2. 왜곡 함수 (연속 함수 f 구현)
        function deform(mx, my, dx, dy) {
            points.forEach(p => {
                const dist = Math.sqrt((mx - p.x)**2 + (my - p.y)**2);
                if (dist < 80) {
                    // 마우스 움직임에 따라 주변 공간을 부드럽게 밀어냄 (Gaussian-like falloff)
                    const force = Math.exp(-dist / 40);
                    p.x += dx * force;
                    p.y += dy * force;

                    // 자기사상(Self-mapping) 유지: 디스크 밖으로 나가지 못하게 제한
                    const distFromCenter = Math.sqrt((p.x - radius)**2 + (p.y - radius)**2);
                    if (distFromCenter > radius - 2) {
                        const angle = Math.atan2(p.y - radius, p.x - radius);
                        p.x = radius + (radius - 2) * Math.cos(angle);
                        p.y = radius + (radius - 2) * Math.sin(angle);
                    }
                }
            });
        }

        // 3. 고정점 계산 (f(x) - x 가 최소인 지점)
        function findFixedPoint() {
            let minDiff = Infinity;
            let target = null;
            points.forEach(p => {
                const diff = Math.sqrt((p.x - p.ox)**2 + (p.y - p.oy)**2);
                if (diff < minDiff) {
                    minDiff = diff;
                    target = p;
                }
            });
            return target;
        }

        // 4. 그리기
        function draw() {
            ctx.clearRect(0, 0, width, width);

            // 가이드라인 (원)
            ctx.beginPath();
            ctx.arc(radius, radius, radius-1, 0, Math.PI*2);
            ctx.strokeStyle = '#ddd';
            ctx.stroke();

            // 왜곡된 격자 그리기 (연속성 시각화)
            ctx.beginPath();
            ctx.lineWidth = 0.5;
            ctx.strokeStyle = '#3498db';
            points.forEach(p => {
                ctx.moveTo(p.x, p.y);
                ctx.arc(p.x, p.y, 2, 0, Math.PI*2);
            });
            ctx.stroke();

            if (showFixed) {
                const fp = findFixedPoint();
                if (fp) {
                    // 원래 위치 표시 (희미하게)
                    ctx.beginPath();
                    ctx.arc(fp.ox, fp.oy, 5, 0, Math.PI*2);
                    ctx.fillStyle = 'rgba(0,0,0,0.2)';
                    ctx.fill();
                    
                    // 현재 위치(고정점) 표시
                    ctx.beginPath();
                    ctx.arc(fp.x, fp.y, 10, 0, Math.PI*2);
                    ctx.strokeStyle = '#ff4757';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                    
                    ctx.fillStyle = '#ff4757';
                    ctx.font = 'bold 14px sans-serif';
                    ctx.fillText("고정점 f(x) ≈ x", fp.x + 15, fp.y + 5);
                }
            }
            requestAnimationFrame(draw);
        }

        // 이벤트 리스너
        canvas.addEventListener('mousedown', () => isDrawing = true);
        window.addEventListener('mouseup', () => isDrawing = false);
        canvas.addEventListener('mousemove', (e) => {
            if (!isDrawing) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            deform(mx, my, e.movementX, e.movementY);
        });

        document.getElementById('resetBtn').onclick = initGrid;
        document.getElementById('fixed-toggle').onclick = function() {
            showFixed = !showFixed;
            this.classList.toggle('active');
        };

        initGrid();
        draw();
    })();
    </script>
</div>