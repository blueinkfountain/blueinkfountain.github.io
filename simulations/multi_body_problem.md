---
layout: default
title: Three-Body Problem Simulation
# parent: Simulations  # (선택 사항) 대분류 이름
nav_order: 1
---

# 🌌 삼체문제 시뮬레이션 (3-Body Problem)

자바스크립트로 구현한 세 천체의 중력 상호작용 모델링입니다.

<!-- 시뮬레이션이 그려질 캔버스 -->
<div style="text-align: center; background: #000; padding: 20px; border-radius: 10px;">
    <canvas id="threeBodyCanvas" width="600" height="600" style="background: #000; max-width: 100%;"></canvas>
    <br>
    <button onclick="resetSim()" style="margin-top: 10px; padding: 8px 16px;">다시 시작 (Reset)</button>
</div>

<!-- 여기에 자바스크립트 코드를 넣습니다 -->
<script>
// 1. 초기 설정 및 변수
const canvas = document.getElementById('threeBodyCanvas');
const ctx = canvas.getContext('2d');

let bodies = [
    { x: 300, y: 200, vx: 0.5, vy: 0, m: 100, color: '#ff4d4d' }, // 천체 1 (빨강)
    { x: 200, y: 400, vx: -0.2, vy: 0.3, m: 100, color: '#4dff4d' }, // 천체 2 (초록)
    { x: 400, y: 400, vx: -0.3, vy: -0.3, m: 100, color: '#4d4dff' }  // 천체 3 (파랑)
];

const G = 1; // 중력 상수 (조절 가능)
const dt = 0.5; // 시간 간격

// 2. 물리 계산 로직
function update() {
    for (let i = 0; i < bodies.length; i++) {
        let fx = 0, fy = 0;
        for (let j = 0; j < bodies.length; j++) {
            if (i === j) continue;
            let dx = bodies[j].x - bodies[i].x;
            let dy = bodies[j].y - bodies[i].y;
            let distSq = dx * dx + dy * dy + 100; // 거리가 너무 가까울 때 튕겨나가는 현상 방지(+100)
            let force = (G * bodies[i].m * bodies[j].m) / distSq;
            let dist = Math.sqrt(distSq);
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

// 3. 그리기 로직
function draw() {
    // 잔상 효과 (배열을 완전히 지우지 않고 반투명하게 덮음)
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let body of bodies) {
        ctx.beginPath();
        ctx.arc(body.x, body.y, 8, 0, Math.PI * 2);
        ctx.fillStyle = body.color;
        ctx.fill();
        ctx.closePath();
    }
}

function loop() {
    update();
    draw();
    requestAnimationFrame(loop);
}

function resetSim() {
    location.reload(); // 가장 간단한 리셋 방식
}

// 실행
loop();
</script>

---

### 시뮬레이션 설명
이 모델은 뉴턴의 만유인력 법칙($F = G \frac{m_1 m_2}{r^2}$)을 오일러 방법을 통해 수치 해석적으로 푼 결과입니다. 세 물체의 질량과 초기 속도가 정교하게 맞물리지 않으면 궤도는 매우 혼돈(Chaos)스러운 양상을 보입니다.