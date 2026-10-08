/* =============================================================================
   CareerBuddy - topic-based Buddy visual (ONE central mapping).

   The landing chatbot shows an animated "stage": Buddy in the middle and five
   labelled pills orbiting it (static/js/BOTscript.js, renderPersistentWelcome).
   This file decides WHICH five pills to show for the department the visitor is
   looking at, so the same animation becomes topic-based - with no change to the
   look, the CSS or the animation. It draws nothing itself and never touches the
   conversation, session, language, voice or any API.

       department open on the page -> topic slug -> BUDDY_TOPICS -> 5 pills
                                         |
                      no / unknown topic -> null -> BOTscript's own landing pills

   THE 30 TOPICS = every department in static/data/it_departments.json (9) and
   static/data/nonit_departments.json (21). A unit test fails if a department is
   added or renamed there without an entry here. Pill labels are short forms of
   each department's real roles.

   PILL ORDER: [top, upper-right, upper-left, lower-left, lower-right] - the
   stage's own slots (n, ne, nw, sw, se). Labels <= 20 characters; the two upper
   side slots sit close to Buddy on phones, so keep those <= 11. Icons must be
   keys of WELCOME_ICONS in BOTscript.js (briefcase user users resume cap book
   building sparkle chart code interview). A test enforces all of this.

   HOW THE CURRENT TOPIC IS FOUND (first match wins; only slugs that exist below
   can ever match, so a URL can never choose arbitrary content):
     1. data-cb-topic on <html>/<body>, or <meta name="cb-topic">  - slug OR the
        department's title; the landing explorer sets this when a department opens
     2. ?topic=<slug>   3. any URL path segment   4. any URL hash segment
   Anything else -> no topic -> the stage keeps its normal landing pills.

   Adding a department: add one entry to BUDDY_TOPICS. Nothing else changes.
   Debug: ?buddyDebug=1 (or localStorage.cbBuddyDebug='1') logs each change.
   ========================================================================== */
(function (root, factory) {
    'use strict';
    var api = factory(root);
    if (typeof module === 'object' && module.exports) {
        module.exports = api;                 // node unit tests: no DOM, no auto-init
    } else {
        root.CBBuddyVisuals = api;
        api.init();
    }
})(typeof window !== 'undefined' ? window : this, function (root) {
    'use strict';

    function deepFreeze(o) {
        Object.keys(o).forEach(function (k) { if (o[k] && typeof o[k] === 'object') deepFreeze(o[k]); });
        return Object.freeze(o);
    }
    function hasOwn(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
    function T(label, pills) {
        return { label: label, nodes: pills.map(function (p) { return { icon: p[0], label: p[1] }; }) };
    }

    /* ----------------------------- THE MAPPING ----------------------------- */
    var BUDDY_TOPICS = deepFreeze({

        /* ---- IT departments (9) ---- */
        'development': T('Development', [['code', 'Software Developer'], ['code', 'Frontend'], ['code', 'Backend'], ['briefcase', 'Mobile Apps'], ['code', 'Full Stack']]),
        'product-management': T('Product Management', [['briefcase', 'Product Manager'], ['chart', 'Growth PM'], ['chart', 'Analyst'], ['code', 'Technical PM'], ['sparkle', 'Product Marketing']]),
        'design-ux-ui': T('Design / UX/UI', [['sparkle', 'UI/UX Designer'], ['sparkle', 'Visual'], ['book', 'UX Research'], ['user', 'Interaction Design'], ['building', 'Design Systems']]),
        'quality-assurance-qa-testing': T('Quality Assurance (QA) / Testing', [['code', 'QA Automation'], ['code', 'SDET'], ['resume', 'Manual QA'], ['chart', 'Performance Testing'], ['user', 'Security Testing']]),
        'devops-infrastructure': T('DevOps / Infrastructure', [['code', 'DevOps Engineer'], ['chart', 'SRE'], ['building', 'Platform'], ['building', 'Cloud Infrastructure'], ['code', 'CI/CD & Release']]),
        'sales-and-marketing': T('Sales and Marketing', [['briefcase', 'Account Executive'], ['users', 'SDR / BDR'], ['chart', 'SEO / SEM'], ['book', 'Content Marketing'], ['sparkle', 'Brand Marketing']]),
        'customer-success-technical-support': T('Customer Success / Technical Support', [['users', 'Customer Success'], ['user', 'L1 Support'], ['resume', 'Onboarding'], ['code', 'Technical Support'], ['sparkle', 'Escalations']]),
        'business-analysis': T('Business Analysis', [['chart', 'Business Analyst'], ['building', 'Systems'], ['chart', 'Data & BI'], ['book', 'Process Analysis'], ['building', 'Business Architect']]),
        'technical-writing': T('Technical Writing', [['book', 'Technical Writer'], ['code', 'API Docs'], ['book', 'UX Writing'], ['resume', 'Technical Editing'], ['code', 'Docs-as-Code']]),

        /* ---- Non-IT, technical (15) ---- */
        'engineering-recruitment-technical-staffing': T('Engineering Recruitment & Technical Staffing', [['users', 'Technical Recruiter'], ['user', 'Sourcing'], ['resume', 'Compliance'], ['building', 'Piping & Mechanical'], ['building', 'Civil & Structural']]),
        'it-digital-technology-staffing': T('IT, Digital & Technology Staffing', [['users', 'Tech Recruiter'], ['code', 'DevOps'], ['chart', 'Data & AI'], ['code', 'Cybersecurity'], ['briefcase', 'Contract Staffing']]),
        'epc-project-workforce-solutions': T('EPC Project Workforce Solutions', [['users', 'EPC Recruitment'], ['briefcase', 'Procurement'], ['chart', 'Planning'], ['user', 'Mobilization'], ['building', 'Site Onboarding']]),
        'pmc-workforce-solutions': T('PMC Workforce Solutions', [['users', 'PMC Recruitment'], ['resume', 'QA/QC'], ['resume', 'Contracts'], ['chart', 'Schedule & Risk'], ['building', 'Owner\'s Engineer']]),
        'hse-fire-industrial-safety-workforce': T('HSE, Fire & Industrial Safety Workforce', [['users', 'HSE Recruitment'], ['sparkle', 'Fire Safety'], ['book', 'Training'], ['user', 'Hygiene'], ['sparkle', 'Emergency Response']]),
        'shutdown-turnaround-rapid-mobilization': T('Shutdown, Turnaround & Rapid Mobilization', [['users', 'Turnaround Staffing'], ['resume', 'Inspection'], ['user', 'Outages'], ['briefcase', 'Rapid Mobilization'], ['user', 'Demobilization']]),
        'plant-operations-maintenance-workforce': T('Plant Operations & Maintenance Workforce', [['building', 'O&M Staffing'], ['user', 'Operations'], ['chart', 'Reliability'], ['code', 'Instrumentation'], ['briefcase', 'Rotating Equipment']]),
        'renewable-energy-workforce-solutions': T('Renewable Energy Workforce Solutions', [['sparkle', 'Renewable Talent'], ['sparkle', 'Wind Energy'], ['sparkle', 'Solar PV'], ['building', 'Battery Storage'], ['sparkle', 'Hydrogen']]),
        'career-buddy-ai-skill-training-talent-platform': T('Career Buddy — AI Skill Training & Talent Platform', [['sparkle', 'AI Talent Platform'], ['chart', 'Growth'], ['resume', 'Assessment'], ['cap', 'Learning Pathways'], ['book', 'Content Ops']]),
        'royal-hrms-ai-payroll-hr-platform': T('Royal HRMS — AI Payroll & HR Platform', [['building', 'AI Payroll & HR'], ['chart', 'Analytics'], ['code', 'Security'], ['briefcase', 'Implementation'], ['users', 'HR Chatbot']]),
        'quality-inspection-skills': T('Quality & Inspection Skills', [['resume', 'QA / QC'], ['resume', 'NDT'], ['user', 'Welding'], ['user', 'Inspection'], ['chart', 'Quality Reporting']]),
        'skilled-technical-trades': T('Skilled & Technical Trades', [['user', 'Electrician'], ['user', 'Welder'], ['user', 'Fitter'], ['user', 'Fabricator'], ['users', 'Site Supervisor']]),
        'automotive-ev-skills': T('Automotive & EV Skills', [['building', 'EV Manufacturing'], ['user', 'Assembly'], ['code', 'Automation'], ['code', 'Electrical Systems'], ['resume', 'Quality Inspection']]),
        'oil-gas-energy-skills': T('Oil & Gas / Energy Skills', [['building', 'Refinery Operations'], ['sparkle', 'HSE'], ['resume', 'Inspection'], ['chart', 'Process Engineering'], ['user', 'Commissioning']]),
        'logistics-industrial-workforce-skills': T('Logistics & Industrial Workforce Skills', [['building', 'Warehouse Operations'], ['chart', 'Inventory'], ['users', 'Supervision'], ['briefcase', 'Material Handling'], ['briefcase', 'Industrial Logistics']]),

        /* ---- Non-IT, non-technical (6) ---- */
        'workforce-outsourcing-managed-staffing': T('Workforce Outsourcing & Managed Staffing', [['users', 'Managed Staffing'], ['briefcase', 'MSP'], ['users', 'Contingent'], ['building', 'Vendor Management'], ['chart', 'Shift Planning']]),
        'recruitment-process-outsourcing-rpo': T('Recruitment Process Outsourcing (RPO)', [['briefcase', 'RPO Account Director'], ['user', 'Sourcing'], ['chart', 'Analytics'], ['sparkle', 'Employer Brand'], ['users', 'Candidate Experience']]),
        'global-workforce-mobility-international-recruitment': T('Global Workforce Mobility & International Recruitment', [['briefcase', 'Global Mobility'], ['resume', 'Visas'], ['building', 'Relocation'], ['users', 'Global Hiring'], ['resume', 'Global Compliance']]),
        'payroll-workforce-administration-support': T('Payroll & Workforce Administration Support', [['briefcase', 'Payroll Operations'], ['resume', 'Timesheets'], ['chart', 'Benefits'], ['resume', 'Payroll Compliance'], ['briefcase', 'Contractor Billing']]),
        'executive-search-leadership-hiring': T('Executive Search & Leadership Hiring', [['user', 'Executive Search'], ['resume', 'Assessment'], ['book', 'Research'], ['users', 'Offer Negotiation'], ['building', 'Board Practice']]),
        'skill-development-workforce-readiness': T('Skill Development & Workforce Readiness', [['cap', 'Workforce Readiness'], ['cap', 'Training'], ['cap', 'Apprentices'], ['book', 'Curriculum Design'], ['resume', 'Trade Certification']])
    });

    /* BOTscript's own landing pills, for reference/tests (BOTscript keeps its own copy as the fallback). */
    var DEFAULT_NODES = deepFreeze([
        { icon: 'resume', label: 'Resume Builder' }, { icon: 'briefcase', label: 'Find Jobs' },
        { icon: 'cap', label: 'Skill Up' }, { icon: 'interview', label: 'Interview Practice' },
        { icon: 'sparkle', label: 'Certifications' }
    ]);

    /* What a click on a topic pill asks Buddy.  {pill} = the pill's label, {topic} = the department's title.
       Edit this one line to change the wording for all 30 departments. */
    var QUESTION_TEMPLATE = 'Tell me about {pill} in {topic}';

    var lastSlug = null;
    var renderedSlug;                    // the topic the chatbot last BUILT its stage with (undefined until it asks)
    var pending = false;
    var initialised = false;

    /* ------------------------------ normalisation ----------------------------- */
    // "Engineering Recruitment & Technical Staffing" -> "engineering-recruitment-technical-staffing"
    function normalizeTopic(value) {
        if (value === null || value === undefined) return '';
        var s = String(value);
        try { s = decodeURIComponent(s); } catch (e) { /* keep raw */ }
        return s.toLowerCase()
            .replace(/\.(html?|php|aspx?)$/, '')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    }

    // A key of BUDDY_TOPICS or null. Own-property check: "constructor", "__proto__" etc. never resolve.
    function lookupSlug(raw) {
        var s = normalizeTopic(raw);
        if (!s) return null;
        var candidates = [s, s.replace(/^\d+-/, '')];      // tolerate "010-<slug>"
        for (var i = 0; i < candidates.length; i++) {
            if (candidates[i] && hasOwn(BUDDY_TOPICS, candidates[i])) return candidates[i];
        }
        return null;
    }

    /* -------------------------------- detection ------------------------------- */
    function readExplicit(doc) {
        if (!doc) return null;
        var meta = doc.querySelector && doc.querySelector('meta[name="cb-topic"]');
        var v = meta && meta.getAttribute('content');
        if (v && v.trim()) return v;
        var holders = [doc.documentElement, doc.body];
        for (var i = 0; i < holders.length; i++) {
            var d = holders[i] && holders[i].getAttribute && holders[i].getAttribute('data-cb-topic');
            if (d && d.trim()) return d;
        }
        return null;
    }

    function fromSegments(str) {
        var parts = String(str || '').split(/[\/?&#]/);
        for (var i = parts.length - 1; i >= 0; i--) {         // most specific segment first
            var slug = lookupSlug(parts[i]);
            if (slug) return slug;
        }
        return null;
    }

    // env is injectable for unit tests: { document, location }
    function detectTopic(env) {
        env = env || {};
        var doc = env.document || root.document;
        var loc = env.location || root.location || {};

        var explicit = readExplicit(doc);
        if (explicit !== null) {                               // the page declared its topic: that wins
            return { slug: lookupSlug(explicit), raw: explicit, source: 'attribute' };
        }
        var q = null;
        try { q = lookupSlug(new URLSearchParams(loc.search || '').get('topic')); } catch (e) { q = null; }
        if (q) return { slug: q, raw: loc.search, source: 'query' };
        var p = fromSegments(loc.pathname);
        if (p) return { slug: p, raw: loc.pathname, source: 'path' };
        var h = fromSegments(loc.hash);
        if (h) return { slug: h, raw: loc.hash, source: 'hash' };
        return { slug: null, raw: '', source: 'none' };
    }

    /* --------------------------------- public API ------------------------------ */
    function getCurrentTopic(env) {
        var t = detectTopic(env);
        return t.slug ? { slug: t.slug, label: BUDDY_TOPICS[t.slug].label, source: t.source } : null;
    }

    // The five {icon, label} pills for the topic being viewed, or null (= use the normal landing pills).
    function getStageNodes(env) {
        var t = detectTopic(env);
        if (!env) renderedSlug = t.slug;   // the stage is being built from this: later changes are measured against it
        return t.slug ? BUDDY_TOPICS[t.slug].nodes : null;
    }

    function questionFor(topicLabel, pillLabel) {
        return QUESTION_TEMPLATE
            .replace('{pill}', function () { return pillLabel; })
            .replace('{topic}', function () { return topicLabel; });
    }

    // The five questions matching getStageNodes(), in the same order, or null when no topic is open.
    function getStageQuestions(env) {
        var t = detectTopic(env);
        if (!t.slug) return null;
        var topic = BUDDY_TOPICS[t.slug];
        return topic.nodes.map(function (n) { return questionFor(topic.label, n.label); });
    }

    // Programmatic way to declare the topic (the landing explorer just sets the attribute itself).
    function setTopic(nameOrSlug) {
        if (!root.document) return;
        root.document.documentElement.setAttribute('data-cb-topic', nameOrSlug == null ? '' : String(nameOrSlug));
    }

    function isDebug() {
        try {
            return root.CB_BUDDY_DEBUG === true ||
                /[?&]buddyDebug=1\b/.test((root.location && root.location.search) || '') ||
                root.localStorage.getItem('cbBuddyDebug') === '1';
        } catch (e) { return false; }
    }

    // Tell the chatbot when the topic changes (only when it really changed).
    function evaluate() {
        var t = detectTopic();
        var shown = renderedSlug !== undefined ? renderedSlug : lastSlug;
        if (t.slug === shown) { lastSlug = t.slug; return; }
        lastSlug = t.slug;
        if (isDebug() && root.console) {
            root.console.info('[BUDDY CONTEXT]\nTopic: ' + (t.slug || '(none)') + '\nSource: ' + t.source +
                '\nPills: ' + (t.slug ? BUDDY_TOPICS[t.slug].nodes.map(function (n) { return n.label; }).join(' | ') : '(landing default)'));
        }
        try {
            root.dispatchEvent(new root.CustomEvent('cb:buddy-topic', {
                detail: { topic: t.slug, label: t.slug ? BUDDY_TOPICS[t.slug].label : null, nodes: t.slug ? BUDDY_TOPICS[t.slug].nodes : null }
            }));
        } catch (e) { /* very old browser: the stage simply keeps its current pills */ }
    }

    function schedule() {              // coalesce bursts of events into one check
        if (pending) return;
        pending = true;
        Promise.resolve().then(function () { pending = false; evaluate(); });
    }

    var PILL_CSS =
        '.riya-visual-node[data-cb-ask]{cursor:pointer;outline:none;-webkit-tap-highlight-color:transparent}' +
        '.riya-visual-node[data-cb-ask] .riya-visual-node-content{transition:background .15s ease,box-shadow .15s ease,filter .15s ease}' +
        '.riya-visual-node[data-cb-ask]:hover .riya-visual-node-content{background:#eef4ff!important;box-shadow:0 6px 16px rgba(24,90,219,.38)!important}' +
        '.riya-visual-node[data-cb-ask]:focus-visible .riya-visual-node-content{box-shadow:0 0 0 2px #fff,0 0 0 4px #185adb!important}' +
        '.riya-visual-node[data-cb-ask]:active .riya-visual-node-content{filter:brightness(.94)}';

    function ensureStyle() {
        var d = root.document;
        if (!d || d.getElementById('cb-pill-style')) return;
        var st = d.createElement('style');
        st.id = 'cb-pill-style';
        st.textContent = PILL_CSS;
        (d.head || d.documentElement).appendChild(st);
    }

    function init() {
        if (initialised || !root.document) return;
        initialised = true;
        ensureStyle();
        lastSlug = detectTopic().slug;
        if (root.MutationObserver) {      // <html> exists already: do not miss a topic set while the page is still parsing
            new root.MutationObserver(schedule).observe(root.document.documentElement, { attributes: true, attributeFilter: ['data-cb-topic'] });
        }

        var run = function () {
            evaluate();                     // anything declared between script load and DOMContentLoaded
            root.addEventListener('popstate', schedule);
            root.addEventListener('hashchange', schedule);
            root.addEventListener('pageshow', schedule);
            root.addEventListener('cb:topic-change', schedule);
            ['pushState', 'replaceState'].forEach(function (m) {
                var orig = root.history && root.history[m];
                if (!orig || orig.__cbBuddyWrapped) return;
                var wrapped = function () { var r = orig.apply(this, arguments); schedule(); return r; };
                wrapped.__cbBuddyWrapped = true;
                root.history[m] = wrapped;
            });
            if (root.MutationObserver) {
                // Deliberately narrow: only the places a topic can be declared. A document-wide observer would
                // fire on every chat message the widget appends.
                var mo = new root.MutationObserver(schedule);
                var attrOnly = { attributes: true, attributeFilter: ['data-cb-topic'] };
                if (root.document.body) mo.observe(root.document.body, attrOnly);
                if (root.document.head) {
                    mo.observe(root.document.head, { childList: true, subtree: true, attributes: true, attributeFilter: ['content'] });
                }
            }
        };
        if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', run);
        else run();
    }

    return {
        BUDDY_TOPICS: BUDDY_TOPICS,
        DEFAULT_NODES: DEFAULT_NODES,
        normalizeTopic: normalizeTopic,
        lookupSlug: lookupSlug,
        detectTopic: detectTopic,
        getCurrentTopic: getCurrentTopic,
        getStageNodes: getStageNodes,
        getStageQuestions: getStageQuestions,
        questionFor: questionFor,
        QUESTION_TEMPLATE: QUESTION_TEMPLATE,
        setTopic: setTopic,
        init: init
    };
});
