// ==============================================================================
// SentinelAI — Application Web Interactive (Temps Réel WebSocket + REST)
// ==============================================================================

let ws = null;
let allEvents = [];
let allUsers = [];
let alarmActive = false;

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initTabs();
    initWebSocket();
    loadStats();
    loadEvents();
    loadUsers();

    // Gestion du formulaire de scan manuel
    const scanForm = document.getElementById("manual-scan-form");
    if (scanForm) {
        scanForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const input = document.getElementById("manual-code-input");
            if (input && input.value.trim()) {
                scanTestCode(input.value.trim());
                input.value = "";
            }
        });
    }

    // Bouton d'acquittement de l'alarme
    const ackBtn = document.getElementById("alarm-ack-btn");
    if (ackBtn) {
        ackBtn.addEventListener("click", () => acknowledgeAlarm());
    }
});

// ------------------------------------------------------------------------------
// 1. Thème Sombre / Clair
// ------------------------------------------------------------------------------
function initTheme() {
    const savedTheme = localStorage.getItem("sentinel_theme") ||
        (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.setAttribute("data-theme", savedTheme);

    const themeBtn = document.getElementById("theme-btn");
    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            localStorage.setItem("sentinel_theme", next);
        });
    }
}

// ------------------------------------------------------------------------------
// 2. Navigation par Onglets
// ------------------------------------------------------------------------------
function initTabs() {
    const navItems = document.querySelectorAll(".nav-item");
    const panels = document.querySelectorAll(".tab-panel");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            navItems.forEach(n => n.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));

            item.classList.add("active");
            const targetId = item.dataset.tab;
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) {
                targetPanel.classList.add("active");
            }

            // Rafraîchir les données selon l'onglet
            if (targetId === "tab-events") loadEvents();
            if (targetId === "tab-users") loadUsers();
            if (targetId === "tab-intrusions") loadEvents();
        });
    });
}

// ------------------------------------------------------------------------------
// 3. WebSocket Temps Réel
// ------------------------------------------------------------------------------
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const indicator = document.getElementById("ros-indicator");
    const statusText = document.getElementById("ros-status-text");

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        if (indicator) {
            indicator.className = "status-dot dot-online";
        }
        if (statusText) statusText.innerText = "Connecté";
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWebSocketMessage(msg);
        } catch (e) {
            console.error("Erreur décodage message WS:", e);
        }
    };

    ws.onclose = () => {
        if (indicator) {
            indicator.className = "status-dot dot-offline";
        }
        if (statusText) statusText.innerText = "Déconnecté (reconnexion...)";
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.warn("Erreur WebSocket:", err);
    };
}

function handleWebSocketMessage(msg) {
    if (msg.type === "access_result") {
        updateAccessDisplay(msg.data);
        loadStats();
        loadEvents();
    } else if (msg.type === "intrusion_info") {
        handleIntrusionAlert(msg.data);
        loadEvents();
    } else if (msg.type === "esp32_status") {
        const espText = document.getElementById("esp32-status-text");
        if (espText) {
            espText.innerText = `ESP32 : OK (${msg.data.uptime || 0}s)`;
        }
    }
}

// ------------------------------------------------------------------------------
// 4. Affichage et Gestion de l'Accès
// ------------------------------------------------------------------------------
function updateAccessDisplay(data) {
    const card = document.getElementById("status-card");
    const badge = document.getElementById("status-badge");
    const icon = document.getElementById("status-icon");
    const name = document.getElementById("user-display-name");
    const grp = document.getElementById("user-display-grp");
    const zone = document.getElementById("user-display-zone");
    const level = document.getElementById("user-display-level");
    const time = document.getElementById("user-display-time");
    const reason = document.getElementById("access-reason");
    const ackBtn = document.getElementById("alarm-ack-btn");

    const isOk = data.status === "ok";
    card.className = `card status-display-card ${isOk ? "granted" : "denied"}`;

    if (isOk) {
        badge.className = "badge badge-success";
        badge.innerText = "ACCÈS ACCORDÉ";
        icon.innerText = "🔓";
        if (ackBtn) ackBtn.classList.add("hidden");
        alarmActive = false;
    } else {
        badge.className = "badge badge-danger";
        badge.innerText = "ACCÈS REFUSÉ";
        icon.innerText = "🚨";
        if (ackBtn) ackBtn.classList.remove("hidden");
        alarmActive = true;
    }

    if (data.user) {
        name.innerText = data.user.name;
        grp.innerText = `Groupe : ${data.user.grp}`;
        zone.innerText = `Zone : ${data.user.zone}`;
        level.innerText = `Niveau : ${data.user.level}`;
    } else {
        name.innerText = `Code : ${data.code_id}`;
        grp.innerText = "Utilisateur Inconnu";
        zone.innerText = "Zone : -";
        level.innerText = "Niveau : -";
    }

    time.innerText = `Heure : ${data.ts ? data.ts.split("T")[1] : ""}`;
    reason.innerText = data.reason || (isOk ? "Accès conforme" : "Refus de sécurité");
}

function handleIntrusionAlert(data) {
    const ackBtn = document.getElementById("alarm-ack-btn");
    if (ackBtn) ackBtn.classList.remove("hidden");
    alarmActive = true;

    // Notification visuelle sur l'onglet Intrusions
    const countBadge = document.getElementById("intrusions-count");
    if (countBadge) {
        const current = parseInt(countBadge.innerText || "0", 10);
        countBadge.innerText = current + 1;
    }
}

// ------------------------------------------------------------------------------
// 5. Actions Utilisateur (Simulation / Scan & Acquittement)
// ------------------------------------------------------------------------------
async function scanTestCode(code) {
    try {
        const resp = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code })
        });
        if (!resp.ok) console.error("Erreur envoi scan :", await resp.text());
    } catch (e) {
        console.error("Erreur fetch scan :", e);
    }
}

async function acknowledgeAlarm() {
    try {
        await fetch("/api/ack", { method: "POST" });
        const ackBtn = document.getElementById("alarm-ack-btn");
        if (ackBtn) ackBtn.classList.add("hidden");
        const card = document.getElementById("status-card");
        if (card) card.classList.remove("denied");
        alarmActive = false;
    } catch (e) {
        console.error("Erreur acquittement alarme :", e);
    }
}

// ------------------------------------------------------------------------------
// 6. Chargement des Données REST (Stats, Events, Users)
// ------------------------------------------------------------------------------
async function loadStats() {
    try {
        const resp = await fetch("/api/stats");
        if (resp.ok) {
            const data = await resp.json();
            document.getElementById("stat-ok").innerText = data.total_granted || 0;
            document.getElementById("stat-denied").innerText = data.total_denied || 0;
            document.getElementById("stat-users").innerText = data.total_users || 0;
        }
    } catch (e) {
        console.warn("Erreur chargement stats :", e);
    }
}

async function loadEvents() {
    try {
        const resp = await fetch("/api/events?limit=50");
        if (resp.ok) {
            allEvents = await resp.json();
            renderEventsTable(allEvents);
            renderIntrusionsGallery(allEvents);
        }
    } catch (e) {
        console.warn("Erreur chargement événements :", e);
    }
}

function renderEventsTable(events) {
    const tbody = document.getElementById("events-tbody");
    if (!tbody) return;

    if (!events || events.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Aucun événement enregistré.</td></tr>`;
        return;
    }

    tbody.innerHTML = events.map(ev => {
        const isOk = ev.status === "ok";
        const dateStr = ev.ts ? ev.ts.replace("T", " ") : "-";
        const statusBadge = isOk
            ? `<span class="badge badge-success">Autorisé</span>`
            : `<span class="badge badge-danger">Refusé</span>`;

        let snapshotCell = "-";
        if (ev.snapshot) {
            const filename = ev.snapshot.split("/").pop();
            snapshotCell = `<img src="/snapshots/${filename}" class="table-thumb" alt="Photo" onclick="openModal('/snapshots/${filename}', 'Intrusion : ${ev.code_id} (${dateStr})')">`;
        }

        return `
            <tr>
                <td>${dateStr}</td>
                <td>${ev.kind || "scan"}</td>
                <td><strong>${ev.code_id || "-"}</strong></td>
                <td>${statusBadge}</td>
                <td>${ev.persons || 0}</td>
                <td>${snapshotCell}</td>
            </tr>
        `;
    }).join("");
}

function renderIntrusionsGallery(events) {
    const gallery = document.getElementById("intrusions-gallery");
    if (!gallery) return;

    const intrusions = events.filter(e => e.status === "denied" && e.snapshot);
    if (intrusions.length === 0) {
        gallery.innerHTML = `<p class="text-muted">Aucune alerte d'intrusion avec capture photo.</p>`;
        return;
    }

    gallery.innerHTML = intrusions.map(ev => {
        const filename = ev.snapshot.split("/").pop();
        const dateStr = ev.ts ? ev.ts.replace("T", " ") : "";
        return `
            <div class="gallery-card" onclick="openModal('/snapshots/${filename}', 'Code: ${ev.code_id} — ${ev.persons} personne(s) — ${dateStr}')">
                <img src="/snapshots/${filename}" alt="Capture">
                <div class="gallery-card-body">
                    <strong>${ev.code_id}</strong>
                    <div class="text-sm text-muted">${dateStr}</div>
                    <div class="badge badge-danger text-sm" style="margin-top:0.3rem;">Intrus: ${ev.persons || 0}</div>
                </div>
            </div>
        `;
    }).join("");
}

function applyFilters() {
    const groupVal = document.getElementById("filter-group").value;
    const statusVal = document.getElementById("filter-status").value;

    let filtered = allEvents;
    if (statusVal !== "all") {
        filtered = filtered.filter(e => e.status === statusVal);
    }
    renderEventsTable(filtered);
}

async function loadUsers() {
    try {
        const resp = await fetch("/api/users");
        if (resp.ok) {
            allUsers = await resp.json();
            renderUsersTable(allUsers);
        }
    } catch (e) {
        console.warn("Erreur chargement utilisateurs :", e);
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById("users-tbody");
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Aucun utilisateur.</td></tr>`;
        return;
    }

    tbody.innerHTML = users.map(u => `
        <tr>
            <td><code>${u.code_id}</code></td>
            <td><strong>${u.name}</strong></td>
            <td>${u.grp}</td>
            <td>${u.level}</td>
            <td>${u.zone}</td>
            <td>${u.active ? '<span class="badge badge-success">Actif</span>' : '<span class="badge badge-idle">Inactif</span>'}</td>
        </tr>
    `).join("");
}

function toggleUserForm() {
    const formCard = document.getElementById("user-form-card");
    if (formCard) formCard.classList.toggle("hidden");
}

async function saveUser(event) {
    event.preventDefault();
    const user = {
        code_id: document.getElementById("form-code").value.trim(),
        name: document.getElementById("form-name").value.trim(),
        grp: document.getElementById("form-grp").value,
        level: parseInt(document.getElementById("form-level").value, 10),
        zone: document.getElementById("form-zone").value,
        active: 1
    };

    try {
        const resp = await fetch("/api/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(user)
        });
        if (resp.ok) {
            toggleUserForm();
            loadUsers();
            loadStats();
        } else {
            alert("Erreur lors de l'enregistrement de l'utilisateur.");
        }
    } catch (e) {
        console.error(e);
    }
}

// ------------------------------------------------------------------------------
// 7. Choix de la Caméra (Laptop vs Extension)
// ------------------------------------------------------------------------------
function updateCameraChoice(index) {
    console.log(`Sélection de la caméra index=${index} (${index === 0 ? "Laptop" : "Extension USB"})`);
    // Rafraîchir le flux en direct
    const streamImg = document.getElementById("mjpeg-stream");
    if (streamImg) {
        streamImg.src = `/api/camera/stream?t=${Date.now()}`;
    }
}

// ------------------------------------------------------------------------------
// 8. Visionneuse Modale
// ------------------------------------------------------------------------------
function openModal(src, caption) {
    const modal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-img");
    const modalCaption = document.getElementById("modal-caption");
    if (modal && modalImg) {
        modalImg.src = src;
        modalCaption.innerText = caption || "";
        modal.classList.remove("hidden");
    }
}

function closeModal() {
    const modal = document.getElementById("image-modal");
    if (modal) modal.classList.add("hidden");
}
