/**
 * earth.js - Procedural Earth Health Canvas Simulator
 *
 * Renders a mathematical 3D-looking rotating globe using HTML5 Canvas.
 * Animates wind/leaf particles or smog/ember particles depending on a
 * dynamic "Earth Health Score" derived from logged actions.
 */

class EarthSimulator {
    /**
     * Initializes the Earth Simulator.
     * @param {string} canvasId - The ID of the HTML Canvas element.
     */
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error("Canvas element not found: " + canvasId);
            return;
        }
        this.ctx = this.canvas.getContext("2d");
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;
        this.radius = 90;

        // Current health score (0 = toxic/dead, 100 = lush/vibrant)
        this.healthScore = 80;
        this.targetHealthScore = 80;

        // Rotation settings
        this.angle = 0;
        this.rotationSpeed = 0.005;

        // Particle systems
        this.particles = [];
        this.maxParticles = 40;

        // Continent definitions (normalized coordinates relative to center, -1 to 1)
        this.continents = [
            // North America / Greenland shape
            [
                { x: -0.6, y: -0.6 }, { x: -0.2, y: -0.7 }, { x: 0.0, y: -0.5 },
                { x: -0.1, y: -0.2 }, { x: -0.3, y: -0.1 }, { x: -0.5, y: -0.3 },
                { x: -0.7, y: -0.4 }
            ],
            // South America shape
            [
                { x: -0.3, y: -0.1 }, { x: -0.1, y: -0.1 }, { x: -0.1, y: 0.2 },
                { x: -0.2, y: 0.5 }, { x: -0.4, y: 0.7 }, { x: -0.4, y: 0.4 },
                { x: -0.5, y: 0.1 }
            ],
            // Eurasia / Africa shape
            [
                { x: 0.1, y: -0.6 }, { x: 0.4, y: -0.7 }, { x: 0.7, y: -0.5 },
                { x: 0.6, y: -0.1 }, { x: 0.3, y: 0.0 }, { x: 0.2, y: 0.3 },
                { x: 0.4, y: 0.6 }, { x: 0.1, y: 0.5 }, { x: 0.0, y: 0.1 }
            ],
            // Australia shape
            [
                { x: 0.5, y: 0.3 }, { x: 0.7, y: 0.3 }, { x: 0.8, y: 0.5 },
                { x: 0.6, y: 0.6 }, { x: 0.5, y: 0.5 }
            ],
            // Extra islands to fill space
            [
                { x: 0.8, y: -0.3 }, { x: 0.9, y: -0.2 }, { x: 0.85, y: -0.1 }
            ]
        ];

        // Start requestAnimationFrame loop
        this.animate();
    }

    /**
     * Updates the health score, triggering transitions.
     * @param {number} newScore - The new target health score (0-100).
     */
    setHealthScore(newScore) {
        this.targetHealthScore = Math.max(0, Math.min(100, newScore));
    }

    /**
     * Spawns a particle based on current health status.
     */
    spawnParticle() {
        if (this.particles.length >= this.maxParticles) return;

        const isHealthy = this.healthScore >= 50;

        if (isHealthy) {
            // Healthy particles: green leaves or cyan sparkles
            const type = Math.random() > 0.5 ? "leaf" : "sparkle";
            this.particles.push({
                type: type,
                x: this.centerX + (Math.random() - 0.5) * this.radius * 1.5,
                y: this.centerY + (Math.random() - 0.5) * this.radius * 1.5,
                vx: 0.2 + Math.random() * 0.6, // Drift right
                vy: -0.2 - Math.random() * 0.4, // Drift up
                size: 3 + Math.random() * 5,
                alpha: 0.8 + Math.random() * 0.2,
                life: 1.0,
                decay: 0.005 + Math.random() * 0.01,
                color: type === "leaf" ? "#10b981" : "#22d3ee",
                rot: Math.random() * Math.PI,
                rotSpeed: (Math.random() - 0.5) * 0.05
            });
        } else {
            // Unhealthy particles: gray soot/smoke or red/orange embers
            const type = Math.random() > 0.6 ? "ember" : "smoke";
            this.particles.push({
                type: type,
                x: this.centerX + (Math.random() - 0.5) * this.radius * 1.2,
                y: this.centerY + this.radius * 0.3 + Math.random() * 20, // Spawn lower
                vx: (Math.random() - 0.5) * 0.4, // Slight horizontal drift
                vy: -0.5 - Math.random() * 0.8, // Rise faster
                size: type === "smoke" ? 6 + Math.random() * 12 : 2 + Math.random() * 3,
                alpha: 0.7 + Math.random() * 0.3,
                life: 1.0,
                decay: 0.008 + Math.random() * 0.015,
                color: type === "smoke" ? "#6b7280" : (Math.random() > 0.5 ? "#f97316" : "#ef4444"),
                rot: Math.random() * Math.PI,
                rotSpeed: (Math.random() - 0.5) * 0.03
            });
        }
    }

    /**
     * Updates all active particles.
     */
    updateParticles() {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= p.decay;
            p.rot += p.rotSpeed;

            if (p.type === "smoke") {
                p.size += 0.15; // Smoke expands
                p.alpha = p.life * 0.4;
            } else {
                p.alpha = p.life;
            }

            // Remove dead particles
            if (p.life <= 0 || p.x < 0 || p.x > this.width || p.y < 0 || p.y > this.height) {
                this.particles.splice(i, 1);
            }
        }

        // Spawn new ones to fill limits
        if (Math.random() < 0.3) {
            this.spawnParticle();
        }
    }

    /**
     * Draws particles behind or in front of Earth.
     * @param {boolean} inFront - Draw front-layer or back-layer.
     */
    drawParticles(inFront) {
        this.ctx.save();
        for (const p of this.particles) {
            // Back particles drift behind Earth, Front particles drift in front
            const distSq = Math.pow(p.x - this.centerX, 2) + Math.pow(p.y - this.centerY, 2);
            const isBehind = distSq < Math.pow(this.radius, 2) && p.vy > 0; // rough heuristic

            if (inFront && isBehind) continue;
            if (!inFront && !isBehind) continue;

            this.ctx.globalAlpha = p.alpha;
            this.ctx.fillStyle = p.color;

            this.ctx.save();
            this.ctx.translate(p.x, p.y);
            this.ctx.rotate(p.rot);

            if (p.type === "leaf") {
                // Draw a small leaf shape
                this.ctx.beginPath();
                this.ctx.ellipse(0, 0, p.size, p.size / 2, 0, 0, Math.PI * 2);
                this.ctx.fill();
            } else if (p.type === "sparkle") {
                // Draw a 4-point star
                this.ctx.beginPath();
                for (let j = 0; j < 4; j++) {
                    this.ctx.lineTo(0, -p.size);
                    this.ctx.rotate(Math.PI / 2);
                }
                this.ctx.closePath();
                this.ctx.fill();
            } else if (p.type === "smoke") {
                // Draw a soft smoke circle
                const grad = this.ctx.createRadialGradient(0, 0, 0, 0, 0, p.size);
                grad.addColorStop(0, p.color);
                grad.addColorStop(1, "rgba(107, 114, 128, 0)");
                this.ctx.fillStyle = grad;
                this.ctx.beginPath();
                this.ctx.arc(0, 0, p.size, 0, Math.PI * 2);
                this.ctx.fill();
            } else {
                // Ember: draw a small flickering block
                this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
            }
            this.ctx.restore();
        }
        this.ctx.restore();
    }

    /**
     * Interpolates between two hex colors.
     */
    interpolateColor(color1, color2, factor) {
        const c1 = parseInt(color1.substring(1), 16);
        const c2 = parseInt(color2.substring(1), 16);

        const r1 = (c1 >> 16) & 255;
        const g1 = (c1 >> 8) & 255;
        const b1 = c1 & 255;

        const r2 = (c2 >> 16) & 255;
        const g2 = (c2 >> 8) & 255;
        const b2 = c2 & 255;

        const r = Math.round(r1 + factor * (r2 - r1));
        const g = Math.round(g1 + factor * (g2 - g1));
        const b = Math.round(b1 + factor * (b2 - b1));

        return `rgb(${r}, ${g}, ${b})`;
    }

    /**
     * Draws the main Earth sphere.
     */
    drawEarth() {
        const factor = this.healthScore / 100;

        // 1. Calculate color palettes based on health
        // Healthy: Rich Emerald/Blue. Degraded: Scorched Grey/Brown/Orange Haze
        const oceanColor = this.interpolateColor("#1e293b", "#1e3a8a", factor); // dark grey-blue to deep blue
        const landColor = this.interpolateColor("#5c4d3c", "#10b981", factor); // muddy brown to lush emerald

        this.ctx.save();

        // 2. Draw Sphere Ocean Base
        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, this.radius, 0, Math.PI * 2);
        this.ctx.fillStyle = oceanColor;
        this.ctx.fill();

        // 3. Clip continents to Earth circle
        this.ctx.clip();

        // 4. Draw continents with orthographic projections
        this.ctx.fillStyle = landColor;
        
        // Loop through each continent template
        for (const continent of this.continents) {
            // Draw continent at different horizontal wrappings
            for (let wrapOffset = -2.0; wrapOffset <= 2.0; wrapOffset += 2.0) {
                this.ctx.beginPath();
                let started = false;

                for (const pt of continent) {
                    // Apply rotation and wrap
                    let x_rot = pt.x + this.angle + wrapOffset;

                    // Project onto sphere: orthographic transformation
                    // x' = x * sqrt(1 - y^2)
                    if (x_rot >= -1.0 && x_rot <= 1.0) {
                        const projX = x_rot * Math.sqrt(1.0 - pt.y * pt.y);
                        
                        // Map normalized -1..1 coordinates to canvas dimensions
                        const canvasX = this.centerX + projX * this.radius;
                        const canvasY = this.centerY + pt.y * this.radius;

                        if (!started) {
                            this.ctx.moveTo(canvasX, canvasY);
                            started = true;
                        } else {
                            this.ctx.lineTo(canvasX, canvasY);
                        }
                    }
                }
                this.ctx.closePath();
                this.ctx.fill();
            }
        }

        // 5. Draw spherical lighting (radial shade overlays)
        const lightGrad = this.ctx.createRadialGradient(
            this.centerX - this.radius * 0.3,
            this.centerY - this.radius * 0.3,
            this.radius * 0.1,
            this.centerX,
            this.centerY,
            this.radius
        );
        lightGrad.addColorStop(0, "rgba(255, 255, 255, 0.15)");
        lightGrad.addColorStop(0.5, "rgba(0, 0, 0, 0.0)");
        lightGrad.addColorStop(1, "rgba(0, 0, 0, 0.65)"); // Dark shadow on right/edges

        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, this.radius, 0, Math.PI * 2);
        this.ctx.fillStyle = lightGrad;
        this.ctx.fill();

        this.ctx.restore();

        // 6. Draw Atmosphere Ring
        const atmosphereColor = this.interpolateColor("#7c2d12", "#06b6d4", factor); // orange/purple halo vs cyan halo
        const glowGrad = this.ctx.createRadialGradient(
            this.centerX, this.centerY, this.radius - 2,
            this.centerX, this.centerY, this.radius + 15
        );
        glowGrad.addColorStop(0, atmosphereColor.replace("rgb", "rgba").replace(")", ", 0.45)"));
        glowGrad.addColorStop(0.3, atmosphereColor.replace("rgb", "rgba").replace(")", ", 0.2)"));
        glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, this.radius + 15, 0, Math.PI * 2);
        this.ctx.fillStyle = glowGrad;
        this.ctx.fill();
    }

    /**
     * Animation frame runner.
     */
    animate() {
        if (!this.ctx) return;

        // Clear canvas
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Smoothly interpolate healthScore to targetHealthScore
        this.healthScore += (this.targetHealthScore - this.healthScore) * 0.05;

        // Increment rotation
        this.angle += this.rotationSpeed;
        if (this.angle > 2.0) {
            this.angle -= 2.0; // Keep inside wrap boundary
        }

        // Draw elements in layers
        this.updateParticles();
        this.drawParticles(false); // Draw back particles
        this.drawEarth();           // Draw Earth globe
        this.drawParticles(true);  // Draw front particles

        // Request next frame
        requestAnimationFrame(() => this.animate());
    }
}

// Export class globally
window.EarthSimulator = EarthSimulator;
