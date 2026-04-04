---
layout: default
title: Brouwer fixed point theorem
parent: Simulations
nav_order: 2
---

#

---

<style>
    #simulation-container {
        text-align: center;
        background: #f9f9f9;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    canvas {
        background: white;
        border-radius: 50%; /* 디스크 모양 */
        border: 2px solid #333;
        cursor: crosshair;
        touch-action: none;
    }
    .controls {
        margin-top: 15px;
    }
    button {
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        background: #4A90E2;
        color: white;
        border: none;
        border-radius: 5px;
        transition: 0.3s;
    }
    button:hover { background: #357ABD; }
    #info { margin-top: 10px; color: #666; font-size: 0.9em; }
</style>

<div id="simulation-container">
    <canvas id="brouwerCanvas" width="400" height="400"></canvas>
    <div class="controls">
        <button onclick="resetPoints()">초기화</button>
        <button onclick="toggleFixedPoint()">고정점 확인</button>
    </div>
    <div id="info">마우스로 점들을 마구 휘저어보세요! 그 다음 고정점을 찾아보세요.</div>
</div>

<script>
    const canvas = document.getElementById('brouwerCanvas');
    const ctx = canvas.getContext('2d');
    const radius = canvas.width / 2;
    const centerX = radius;
    const centerY = radius;
    
    let points = [];
    const numPoints = 800; // 점의 개수
    let showFixedPoint = false;

    class Point {
        constructor() {
            // 원 안에 랜덤하게 배치
            let r = Math.sqrt(Math.random()) * (radius - 5);
            let theta = Math.random() * 2 * Math.PI;
            this.originX = centerX + r * Math.cos(theta);
            this.originY = centerY + r * Math.sin(theta);
            this.x = this.originX;
            this.y = this.originY;
            this.color = `hsl(${Math.random() * 360}, 70%, 60%)`;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, 3, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.fill();
            ctx.closePath();
        }

        update(mouseX, mouseY, isMouseDown) {
            if (isMouseDown) {
                let dx = mouseX - this.x;
                let dy = mouseY - this.y;
                let dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 60) { // 마우스 근처의 점들만 이동
                    this.x += dx * 0.1;
                    this.y += dy * 0.1;
                    
                    // 원 밖으로 나가지 않게 제한
                    let distFromCenter = Math.sqrt(Math.pow(this.x - centerX, 2) + Math.pow(this.y - centerY, 2));
                    if (distFromCenter > radius - 5) {
                        let angle = Math.atan2(this.y - centerY, this.x - centerX);
                        this.x = centerX + (radius - 5) * Math.cos(angle);
                        this.y = centerY + (radius - 5) * Math.sin(angle);
                    }
                }
            }
        }

        getDistance() {
            return Math.sqrt(Math.pow(this.x - this.originX, 2) + Math.pow(this.y - this.originY, 2));
        }
    }

    function init() {
        points = [];
        for (let i = 0; i < numPoints; i++) {
            points.push(new Point());
        }
    }

    function resetPoints() {
        init();
        showFixedPoint = false;
    }

    function toggleFixedPoint() {
        showFixedPoint = !showFixedPoint;
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

    // 터치 지원
    canvas.addEventListener('touchstart', (e) => { isMouseDown = true; e.preventDefault(); });
    canvas.addEventListener('touchend', () => isMouseDown = false);
    canvas.addEventListener('touchmove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouseX = e.touches[0].clientX - rect.left;
        mouseY = e.touches[0].clientY - rect.top;
        e.preventDefault();
    });

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // 원 가이드라인
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.strokeStyle = '#eee';
        ctx.stroke();

        let minDrawDist = Infinity;
        let fixedPoint = null;

        points.forEach(p => {
            p.update(mouseX, mouseY, isMouseDown);
            p.draw();
            
            let d = p.getDistance();
            if (d < minDrawDist) {
                minDrawDist = d;
                fixedPoint = p;
            }
        });

        if (showFixedPoint && fixedPoint) {
            // 고정점 강조 효과
            ctx.beginPath();
            ctx.arc(fixedPoint.x, fixedPoint.y, 15, 0, Math.PI * 2);
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            ctx.fillStyle = 'red';
            ctx.font = 'bold 16px Arial';
            ctx.fillText("Fixed Point!", fixedPoint.x + 20, fixedPoint.y);
        }

        requestAnimationFrame(animate);
    }

    init();
    animate();
</script>