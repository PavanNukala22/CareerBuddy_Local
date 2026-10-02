/* ============================================================================
 * Riya / Buddy — embeddable assistant for the static "Skill Up" hub pages
 * (English & Vocab, Aptitude, Tech, Sitemap, CEFR, Vocabulary, etc.).
 *
 * These pages are plain static HTML served from /static/... and never pass
 * through Django's base.html, so the normal widget (templates/includes/
 * aria_assistant.html + BOTscript.js) is not present on them.
 *
 * This single script rebuilds a lightweight Buddy widget inside a Shadow DOM
 * (so the many different page styles can't break it) and talks to the same
 * backend the main widget uses:
 *     POST /api/riya/chat/        -> { message, reply, actions, audio, speak }
 * The endpoint is @csrf_exempt, so a same-origin fetch needs no CSRF token.
 *
 * Master-prompt contract honoured here:
 *   - Voice output for EVERY response, whether the user typed or spoke.
 *   - Navigation: speak the confirmation first, then navigate.
 *   - Conversation persists across hub page loads (sessionStorage).
 * ==========================================================================*/
(function () {
    "use strict";

    // Never inject twice, and never collide with the Django widget if it loads.
    if (window.__riyaEmbedLoaded || document.getElementById("riya-embed-root")) {
        return;
    }
    window.__riyaEmbedLoaded = true;

    var API_CHAT = "/api/riya/chat/";
    var STORE_KEY = "riya_embed_state_v1";

    var LANGUAGES = [
        { id: "english", label: "English", speech: "en-US" },
        { id: "hindi", label: "हिन्दी", speech: "hi-IN" },
        { id: "telugu", label: "తెలుగు", speech: "te-IN" },
        { id: "tamil", label: "தமிழ்", speech: "ta-IN" },
        { id: "arabic", label: "العربية", speech: "ar-SA" },
        { id: "russian", label: "Русский", speech: "ru-RU" },
        { id: "vietnamese", label: "Tiếng Việt", speech: "vi-VN" }
    ];

    // ── Persisted state (kept across full page loads within the hub) ──────────
    var state = { open: false, language: "english", messages: [] };
    try {
        var saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || "null");
        if (saved && typeof saved === "object") {
            state.open = !!saved.open;
            state.language = saved.language || "english";
            state.messages = Array.isArray(saved.messages) ? saved.messages.slice(-40) : [];
        }
    } catch (e) { /* ignore corrupt state */ }

    function persist() {
        try {
            sessionStorage.setItem(STORE_KEY, JSON.stringify({
                open: state.open,
                language: state.language,
                messages: state.messages.slice(-40)
            }));
        } catch (e) { /* storage full / disabled — non-fatal */ }
    }

    function speechLangFor(id) {
        for (var i = 0; i < LANGUAGES.length; i++) {
            if (LANGUAGES[i].id === id) return LANGUAGES[i].speech;
        }
        return "en-US";
    }

    // ── Build the widget inside a Shadow DOM ──────────────────────────────────
    var host = document.createElement("div");
    host.id = "riya-embed-root";
    host.style.cssText = "position:fixed;z-index:2147483000;bottom:0;right:0;";
    (document.body || document.documentElement).appendChild(host);
    var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;

    var CSS = "" +
        ":host{ all: initial; }" +
        "*{ box-sizing:border-box; font-family: 'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif; }" +
        ".launcher{ position:fixed; right:22px; bottom:22px; width:60px; height:60px; border-radius:50%;" +
        "  border:none; cursor:pointer; background:linear-gradient(145deg,#2f6df6,#1b4fd6); color:#fff;" +
        "  box-shadow:0 10px 26px rgba(27,79,214,.42); display:flex; align-items:center; justify-content:center;" +
        "  transition:transform .18s ease, box-shadow .18s ease; }" +
        ".launcher:hover{ transform:translateY(-2px) scale(1.04); box-shadow:0 14px 32px rgba(27,79,214,.5); }" +
        ".launcher svg{ width:30px; height:30px; }" +
        ".panel{ position:fixed; right:22px; bottom:92px; width:360px; max-width:calc(100vw - 24px);" +
        "  height:520px; max-height:calc(100vh - 120px); background:#fff; border-radius:18px; overflow:hidden;" +
        "  box-shadow:0 24px 60px rgba(15,23,42,.28); display:none; flex-direction:column;" +
        "  border:1px solid #e6eaf2; }" +
        ".panel.open{ display:flex; animation:pop .18s ease; }" +
        "@keyframes pop{ from{ transform:translateY(10px); opacity:.4 } to{ transform:none; opacity:1 } }" +
        ".hd{ display:flex; align-items:center; gap:8px; padding:12px 14px; background:#f7f9fc; border-bottom:1px solid #eef1f7; }" +
        ".hd .robot{ width:30px; height:30px; border-radius:50%; background:linear-gradient(145deg,#2f6df6,#1b4fd6);" +
        "  display:flex; align-items:center; justify-content:center; color:#fff; flex:0 0 auto; }" +
        ".hd .robot svg{ width:18px; height:18px; }" +
        ".hd .name{ font-weight:700; color:#0f172a; font-size:15px; }" +
        ".hd select{ margin-left:auto; font-size:12px; padding:3px 6px; border:1px solid #d7deea; border-radius:8px;" +
        "  background:#fff; color:#334155; cursor:pointer; }" +
        ".hd .x{ border:none; background:transparent; cursor:pointer; color:#64748b; font-size:20px; line-height:1;" +
        "  width:28px; height:28px; border-radius:8px; }" +
        ".hd .x:hover{ background:#eceff5; color:#0f172a; }" +
        ".body{ flex:1; overflow-y:auto; padding:14px; background:#fbfcfe; display:flex; flex-direction:column; gap:10px; }" +
        ".msg{ max-width:86%; padding:9px 12px; border-radius:14px; font-size:13.5px; line-height:1.45; white-space:pre-wrap; word-wrap:break-word; }" +
        ".msg.bot{ align-self:flex-start; background:#fff; border:1px solid #e8ecf4; color:#1f2937; border-bottom-left-radius:5px; }" +
        ".msg.me{ align-self:flex-end; background:#e8f0ff; border:1px solid #cfe0ff; color:#123; border-bottom-right-radius:5px; }" +
        ".msg.typing{ color:#64748b; font-style:italic; }" +
        ".chips{ display:flex; flex-wrap:wrap; gap:6px; }" +
        ".chip{ border:1px solid #c9d8ff; background:#f2f6ff; color:#1b4fd6; font-size:12px; font-weight:600;" +
        "  padding:6px 10px; border-radius:999px; cursor:pointer; }" +
        ".chip:hover{ background:#e3ecff; }" +
        ".ft{ border-top:1px solid #eef1f7; padding:10px; background:#fff; }" +
        ".row{ display:flex; align-items:center; gap:8px; }" +
        ".mic{ width:38px; height:38px; flex:0 0 auto; border-radius:50%; border:1px solid #d7deea; background:#fff;" +
        "  cursor:pointer; display:flex; align-items:center; justify-content:center; color:#1b4fd6; }" +
        ".mic.rec{ background:#ffe9e9; border-color:#ffb4b4; color:#d11; animation:pulse 1s infinite; }" +
        "@keyframes pulse{ 0%{ box-shadow:0 0 0 0 rgba(221,17,17,.4) } 70%{ box-shadow:0 0 0 8px rgba(221,17,17,0) } 100%{ box-shadow:0 0 0 0 rgba(221,17,17,0) } }" +
        ".mic svg{ width:18px; height:18px; }" +
        ".inp{ flex:1; border:1px solid #d7deea; border-radius:999px; padding:9px 14px; font-size:13.5px; outline:none; }" +
        ".inp:focus{ border-color:#2f6df6; box-shadow:0 0 0 3px rgba(47,109,246,.15); }" +
        ".send{ width:38px; height:38px; flex:0 0 auto; border-radius:50%; border:none; cursor:pointer;" +
        "  background:linear-gradient(145deg,#2f6df6,#1b4fd6); color:#fff; display:flex; align-items:center; justify-content:center; }" +
        ".send:disabled{ opacity:.5; cursor:default; }" +
        ".send svg{ width:18px; height:18px; }" +
        ".sr{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }";

    var ROBOT_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="12" rx="3"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1.4" fill="currentColor" stroke="none"/><circle cx="8.5" cy="14" r="1.3" fill="currentColor" stroke="none"/><circle cx="15.5" cy="14" r="1.3" fill="currentColor" stroke="none"/></svg>';
    var MIC_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 17v4"/></svg>';
    var SEND_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>';

    var langOptions = LANGUAGES.map(function (l) {
        return '<option value="' + l.id + '"' + (l.id === state.language ? " selected" : "") + ">" + l.label + "</option>";
    }).join("");

    var wrap = document.createElement("div");
    wrap.innerHTML =
        "<style>" + CSS + "</style>" +
        '<button class="launcher" part="launcher" aria-label="Open Buddy assistant">' + ROBOT_SVG + "</button>" +
        '<section class="panel" role="dialog" aria-label="Buddy assistant">' +
        '<header class="hd">' +
        '<span class="robot">' + ROBOT_SVG + "</span>" +
        '<span class="name">Buddy</span>' +
        '<select class="lang" aria-label="Assistant language">' + langOptions + "</select>" +
        '<button class="x" aria-label="Close assistant">&times;</button>' +
        "</header>" +
        '<div class="body" aria-live="polite"></div>' +
        '<footer class="ft">' +
        '<div class="row">' +
        '<button class="mic" aria-label="Speak to Buddy" title="Click to speak">' + MIC_SVG + "</button>" +
        '<input class="inp" type="text" placeholder="Type a message..." aria-label="Message Buddy" maxlength="1000" />' +
        '<button class="send" aria-label="Send message" title="Send">' + SEND_SVG + "</button>" +
        "</div>" +
        "</footer>" +
        "</section>";
    root.appendChild(wrap);

    var $ = function (sel) { return root.querySelector(sel); };
    var launcher = $(".launcher");
    var panel = $(".panel");
    var bodyEl = $(".body");
    var langSel = $(".lang");
    var input = $(".inp");
    var sendBtn = $(".send");
    var micBtn = $(".mic");
    var closeBtn = $(".x");

    // ── Rendering ─────────────────────────────────────────────────────────────
    function scrollDown() { bodyEl.scrollTop = bodyEl.scrollHeight; }

    function addBubble(role, text) {
        var el = document.createElement("div");
        el.className = "msg " + (role === "user" ? "me" : "bot");
        el.textContent = text;
        bodyEl.appendChild(el);
        scrollDown();
        return el;
    }

    function renderChips(actions, onPick) {
        if (!actions || !actions.length) return;
        var box = document.createElement("div");
        box.className = "chips";
        actions.forEach(function (a) {
            if (!a || !a.route) return;
            var b = document.createElement("button");
            b.className = "chip";
            b.textContent = a.label || "Open";
            b.addEventListener("click", function () { onPick(a); });
            box.appendChild(b);
        });
        if (box.children.length) { bodyEl.appendChild(box); scrollDown(); }
    }

    function restore() {
        bodyEl.innerHTML = "";
        if (!state.messages.length) {
            addBubble("assistant", "Hi! I'm Buddy. Ask me to open English & Vocab, Aptitude, Tech, the Sitemap, or any learning section.");
        } else {
            state.messages.forEach(function (m) { addBubble(m.role, m.text); });
        }
    }

    // ── Speech (always on, per spec) ──────────────────────────────────────────
    var ttsAudio = new Audio();
    function stopSpeaking() {
        try { ttsAudio.pause(); ttsAudio.currentTime = 0; ttsAudio.removeAttribute("src"); } catch (e) { }
        if (window.speechSynthesis) { try { window.speechSynthesis.cancel(); } catch (e) { } }
    }

    function speak(text, audioB64, done) {
        var finished = false;
        function finish() { if (finished) return; finished = true; if (typeof done === "function") done(); }
        if (!text) { finish(); return; }
        stopSpeaking();

        if (audioB64) {
            try {
                ttsAudio.src = "data:audio/wav;base64," + audioB64;
                ttsAudio.onended = finish;
                ttsAudio.onerror = function () { speakBrowser(text, finish); };
                var p = ttsAudio.play();
                if (p && p.catch) p.catch(function () { speakBrowser(text, finish); });
                return;
            } catch (e) { /* fall through to browser voice */ }
        }
        speakBrowser(text, finish);
    }

    function speakBrowser(text, done) {
        if (!("speechSynthesis" in window)) { done(); return; }
        try {
            var u = new SpeechSynthesisUtterance(text);
            u.lang = speechLangFor(state.language);
            u.rate = 1; u.pitch = 1;
            u.onend = done; u.onerror = done;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
        } catch (e) { done(); }
    }

    // ── Navigation ────────────────────────────────────────────────────────────
    function go(route) {
        if (!route) return;
        try { window.location.assign(route); } catch (e) { window.location.href = route; }
    }

    // ── Talk to the backend ───────────────────────────────────────────────────
    var busy = false;

    function send(text, inputMode) {
        text = (text || "").replace(/\s+/g, " ").trim();
        if (!text || busy) return;
        busy = true; sendBtn.disabled = true;

        addBubble("user", text);
        state.messages.push({ role: "user", text: text });
        persist();

        var typing = document.createElement("div");
        typing.className = "msg bot typing";
        typing.textContent = "Buddy is thinking…";
        bodyEl.appendChild(typing);
        scrollDown();

        fetch(API_CHAT, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                page: "skillup_static",
                path: window.location.pathname + window.location.hash,
                input_mode: inputMode || "text",
                language: state.language,
                want_audio: true
            })
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                typing.remove();
                var reply = (data && (data.message || data.reply)) || "I couldn't find that in Career Buddy.";
                addBubble("assistant", reply);
                state.messages.push({ role: "assistant", text: reply });
                persist();

                var actions = (data && data.actions) || [];
                var navAction = null;
                for (var i = 0; i < actions.length; i++) {
                    if (actions[i] && actions[i].route) { navAction = actions[i]; break; }
                }
                // Show action chips the user can click too.
                renderChips(actions, function (a) { go(a.route); });

                // Voice output for EVERY response; navigate only after speech ends.
                speak(reply, data && data.audio, function () {
                    if (navAction && (data.source === "intent" || actions.length === 1)) {
                        go(navAction.route);
                    }
                });
            })
            .catch(function () {
                typing.remove();
                var msg = "I'm having trouble reaching the assistant right now. Please try again.";
                addBubble("assistant", msg);
                speak(msg, null);
            })
            .then(function () { busy = false; sendBtn.disabled = false; input.focus(); });
    }

    // ── Voice input (browser SpeechRecognition) ───────────────────────────────
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recog = null, recording = false;
    if (!SR) { micBtn.style.display = "none"; }

    function startRec() {
        if (!SR || recording) return;
        stopSpeaking();
        recog = new SR();
        recog.lang = speechLangFor(state.language);
        recog.interimResults = false;
        recog.maxAlternatives = 1;
        recording = true;
        micBtn.classList.add("rec");
        recog.onresult = function (ev) {
            var t = "";
            for (var i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
            if (t.trim()) send(t, "voice");
        };
        recog.onerror = stopRec;
        recog.onend = stopRec;
        try { recog.start(); } catch (e) { stopRec(); }
    }
    function stopRec() {
        recording = false;
        micBtn.classList.remove("rec");
        if (recog) { try { recog.stop(); } catch (e) { } recog = null; }
    }

    // ── Open / close ──────────────────────────────────────────────────────────
    function open() {
        state.open = true; persist();
        panel.classList.add("open");
        launcher.style.display = "none";
        restore();
        setTimeout(function () { input.focus(); }, 60);
    }
    function close() {
        state.open = false; persist();
        panel.classList.remove("open");
        launcher.style.display = "flex";
        stopSpeaking(); stopRec();
    }

    // ── Wire events ───────────────────────────────────────────────────────────
    launcher.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    sendBtn.addEventListener("click", function () { var v = input.value; input.value = ""; send(v, "text"); });
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); var v = input.value; input.value = ""; send(v, "text"); }
    });
    micBtn.addEventListener("click", function () { recording ? stopRec() : startRec(); });
    langSel.addEventListener("change", function () { state.language = langSel.value; persist(); });

    // Restore open-state across hub page loads.
    if (state.open) { open(); } else { restore(); /* pre-build so it's instant */ bodyEl.innerHTML = ""; }
})();
