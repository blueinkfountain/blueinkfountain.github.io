---
layout: default
title: Three-Body Problem Simulation
parent: Simulations
nav_order: 1
---

# 🌌 삼체문제 시뮬레이션 (3-Body Problem)


<div markdown="0" style="text-align: center; background: #000; padding: 20px; border-radius: 10px;">
    <canvas id="threeBodyCanvas" width="600" height="600" style="background: #000; max-width: 100%; border: 1px solid #333;"></canvas>
    <br>
    <button id="resetBtn" style="margin-top: 15px; padding: 10px 20px; cursor: pointer; border-radius: 5px; border: none; background: #444; color: white;">시뮬레이션 재시작</button>
</div>

<!-- Jekyll이 코드를 건드리지 못하게 div로 감쌉니다 -->
<div markdown="0">
<script>
(function() {
    const canvas = document.getElementById('threeBodyCanvas');
    const ctx = canvas.getContext('2d');
    const resetBtn = document.getElementById('resetBtn');

    let bodies = [];

    function init() {
        bodies = [
            { x: 300, y: 250, vx: 0.4, vy: 0, m: 150, color: '#ff4d4d' }, 
            { x: 200, y: 400, vx: -0.2, vy: 0.3, m: 150, color: '#4dff4d' },
            { x: 400, y: 400, vx: -0.2, vy: -0.3, m: 150, color: '#4d4dff' }
        ];
    }

    const G = 1.2; 
    const dt = 0.6;

    function update() {
        for (let i = 0; i < bodies.length; i++) {
            let fx = 0, fy = 0;
            for (let j = 0; j < bodies.length; j++) {
                if (i === j) continue;
                let dx = bodies[j].x - bodies[i].x;
                let dy = bodies[j].y - bodies[i].y;
                let distSq = dx * dx + dy * dy + 100; 
                let dist = Math.sqrt(distSq);
                let force = (G * bodies[i].m * bodies[j].m) / distSq;
                fx += force * (dx / dist);
                fy += force * (dy / dist);
            }
            bodies[i].vx += (fx / bodies[i].m) * dt;
            bodies[i].vy += (fy / bodies[i].m) * dt;
        }

        for (let body of bodies) {
            body.x += body.vx * dt;
            body.y += body.vy * dt;
        }
    }

    function draw() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'; // 궤적이 더 길게 남도록 수정
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for (let body of bodies) {
            ctx.beginPath();
            ctx.arc(body.x, body.y, 10, 0, Math.PI * 2);
            ctx.fillStyle = body.color;
            ctx.shadowBlur = 15;
            ctx.shadowColor = body.color;
            ctx.fill();
            ctx.closePath();
        }
    }

    function loop() {
        update();
        draw();
        requestAnimationFrame(loop);
    }

    resetBtn.addEventListener('click', init);

    init();
    loop();
})();
</script>
</div>

---