/**
 * app.js - Client state management, event handling, and API communication.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize global instances
    let earthSim = null;
    if (window.EarthSimulator) {
        earthSim = new window.EarthSimulator("earth-canvas");
    }

    // State
    let actionsHistory = [];
    let currentStreak = 0;
    let earthHealth = 80;

    // DOM Elements
    const logButtons = document.querySelectorAll(".log-btn");
    const nudgeText = document.getElementById("nudge-text");
    const srNudgeLive = document.getElementById("sr-nudge-live");
    const earthHealthText = document.getElementById("earth-health-text");
    const streakText = document.getElementById("streak-text");
    const totalCo2Text = document.getElementById("total-co2-text");
    const insightContent = document.getElementById("insight-content");
    const insightSourceText = document.getElementById("insight-source-text");
    const refreshInsightBtn = document.getElementById("refresh-insight-btn");
    const translateInsightBtn = document.getElementById("translate-insight-btn");
    const translateLang = document.getElementById("translate-lang");
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    const historyTableBody = document.getElementById("history-table-body");

    // 2. Fetch action history
    async function fetchHistory() {
        try {
            const response = await fetch("/api/actions");
            if (response.ok) {
                actionsHistory = await response.json();
                renderHistory();
                recalculateStateFromHistory();
            }
        } catch (error) {
            console.error("Error fetching action history:", error);
        }
    }

    // 3. Recalculate health and streak based on history
    function recalculateStateFromHistory() {
        currentStreak = 0;
        earthHealth = 80; // Reset base health
        let totalCo2 = 0;

        // Process in chronological order (oldest first) to build streak
        const chronological = [...actionsHistory].reverse();
        for (const action of chronological) {
            totalCo2 += action.co2_kg;
            if (action.co2_kg <= 1.0) {
                currentStreak++;
                earthHealth = Math.min(100, earthHealth + 5);
            } else {
                currentStreak = 0;
                earthHealth = Math.max(10, earthHealth - 10);
            }
        }

        // Update UI
        totalCo2Text.innerText = `${totalCo2.toFixed(2)} kg`;
        
        // Update Earth Visualizer
        if (earthSim) {
            earthSim.setHealthScore(earthHealth);
        }

        // Update Atmospheric Text State
        updateHealthText(earthHealth);

        // Update Streak Text
        if (currentStreak > 0) {
            streakText.innerText = `${currentStreak} Low-Emission Choice${currentStreak > 1 ? "s" : ""}!`;
            streakText.className = "metric-value health-excellent";
        } else {
            streakText.innerText = "Balanced Commences";
            streakText.className = "metric-value";
        }
    }

    // 4. Update the Earth health description text and styles
    function updateHealthText(health) {
        earthHealthText.innerText = getHealthLabel(health);
        
        // Remove old classes
        earthHealthText.className = "metric-value";
        
        // Add new class based on health value
        if (health >= 80) {
            earthHealthText.classList.add("health-excellent");
        } else if (health >= 50) {
            earthHealthText.classList.add("health-moderate");
        } else if (health >= 30) {
            earthHealthText.classList.add("health-warning");
        } else {
            earthHealthText.classList.add("health-degraded");
        }
    }

    function getHealthLabel(health) {
        if (health >= 80) return "Vibrant & Clean";
        if (health >= 50) return "Stable (Moderate Smog)";
        if (health >= 30) return "Compromised Haze";
        return "Severe Pollutant Alert";
    }

    // 5. Render action history table
    function renderHistory() {
        if (actionsHistory.length === 0) {
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-table-msg">No actions logged yet. Your carbon history will appear here.</td>
                </tr>
            `;
            return;
        }

        historyTableBody.innerHTML = actionsHistory
            .map((action) => {
                const date = new Date(action.timestamp);
                const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                
                // Styling the CO2 number
                const co2Class = action.co2_kg <= 1.0 ? "health-excellent" : (action.co2_kg > 5.0 ? "health-degraded" : "health-warning");

                return `
                    <tr>
                        <td><strong>${timeStr}</strong> <span class="btn-sub">${dateStr}</span></td>
                        <td><span class="metric-value">${capitalize(action.category)}</span></td>
                        <td>${capitalize(action.type)}</td>
                        <td>${action.amount} ${action.unit}</td>
                        <td><strong class="${co2Class}">${action.co2_kg.toFixed(3)}</strong></td>
                        <td><span class="text-secondary">${action.nudge}</span></td>
                    </tr>
                `;
            })
            .join("");
    }

    // 6. Fetch weekly reduction lever insight
    async function fetchWeeklyInsight() {
        try {
            insightContent.innerHTML = `<p class="text-secondary">Analyzing your habits to calculate optimal reduction levers...</p>`;
            const response = await fetch("/api/insights");
            if (response.ok) {
                const data = await response.json();
                insightContent.innerHTML = `<p>${data.insight}</p>`;
                insightSourceText.innerText = capitalize(data.source);
            } else {
                insightContent.innerHTML = `<p class="health-degraded">Failed to generate insights. Please try logging more activities.</p>`;
                insightSourceText.innerText = "Error";
            }
        } catch (error) {
            console.error("Error fetching insights:", error);
            insightContent.innerHTML = `<p class="health-degraded">Network error while fetching weekly recommendations.</p>`;
            insightSourceText.innerText = "Connection lost";
        }
    }

    // 7. Log a new carbon action
    async function logAction(category, type, amount, unit) {
        try {
            const response = await fetch("/api/actions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ category, type, amount, unit }),
            });

            if (response.ok) {
                const loggedAction = await response.json();

                // Add to history and refresh history logs
                actionsHistory.unshift(loggedAction);
                renderHistory();
                recalculateStateFromHistory();

                // Trigger a visual nudge animation flash
                const nudgeContainer = document.querySelector(".nudge-container");
                nudgeContainer.style.animation = "none";
                // Trigger reflow to restart keyframe animation
                void nudgeContainer.offsetWidth; 
                nudgeContainer.style.animation = "nudgeFlash 0.6s ease-out";

                // Update nudge text
                nudgeText.innerText = loggedAction.nudge;
                
                // Accessibility: announce nudge politely to screen readers
                srNudgeLive.innerText = `New action logged. Impact nudge: ${loggedAction.nudge}`;

                // Trigger background refresh of insight
                fetchWeeklyInsight();
            } else {
                const errData = await response.json();
                alert(`Error logging action: ${errData.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Error logging action:", error);
            alert("Connection error: Failed to reach the server.");
        }
    }

    // 8. Clear actions history
    async function clearHistory() {
        if (!confirm("Are you sure you want to clear your entire carbon action log? This cannot be undone.")) {
            return;
        }

        try {
            const response = await fetch("/api/actions/clear", {
                method: "POST"
            });
            if (response.ok) {
                actionsHistory = [];
                renderHistory();
                recalculateStateFromHistory();
                nudgeText.innerText = "History cleared. Tap any button above to log a new action.";
                srNudgeLive.innerText = "Action history has been cleared.";
                fetchWeeklyInsight();
            } else {
                alert("Failed to clear action history.");
            }
        } catch (error) {
            console.error("Error clearing history:", error);
            alert("Connection error: Failed to clear history.");
        }
    }

    // Bind event listeners to log buttons
    logButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const cat = btn.getAttribute("data-category");
            const type = btn.getAttribute("data-type");
            const amount = parseFloat(btn.getAttribute("data-amount"));
            const unit = btn.getAttribute("data-unit");

            // Add visual active bounce animation
            btn.style.transform = "scale(0.95)";
            setTimeout(() => {
                btn.style.transform = "";
            }, 100);

            logAction(cat, type, amount, unit);
        });

        // Accessible keyboard triggers
        btn.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                btn.click();
            }
        });
    });

    // Refresh insight bind
    refreshInsightBtn.addEventListener("click", () => {
        // Spin refresh button icon
        const icon = refreshInsightBtn.querySelector("i");
        icon.style.transform = "rotate(360deg)";
        icon.style.transition = "transform 0.5s ease-out";
        setTimeout(() => {
            icon.style.transform = "";
            icon.style.transition = "";
        }, 500);

        fetchWeeklyInsight();
    });

    // Clear history bind
    clearHistoryBtn.addEventListener("click", clearHistory);

    // Check translation availability and show button if available
    fetch("/health").then(r => r.json()).then(data => {
        if (data.services && data.services.translation === "connected") {
            translateInsightBtn.style.display = "flex";
        }
    }).catch(() => {});

    // Translate insight button
    if (translateInsightBtn) {
        translateInsightBtn.addEventListener("click", async () => {
            const currentText = insightContent.querySelector("p")?.innerText;
            if (!currentText) return;
            const lang = translateLang ? translateLang.value : "hi";
            try {
                const resp = await fetch("/api/translate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text: currentText, target: lang }),
                });
                const data = await resp.json();
                if (resp.ok) {
                    insightContent.innerHTML = `<p>${data.translated}</p>`;
                } else if (data.available === false) {
                    translateInsightBtn.style.display = "none";
                }
            } catch (e) {
                console.error("Translation error:", e);
            }
        });
    }

    // Initial page load triggers
    fetchHistory();
    fetchWeeklyInsight();

    // Helper functions
    function capitalize(str) {
        if (!str) return "";
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Initialize Lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
