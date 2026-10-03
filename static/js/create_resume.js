/* Create Resume builder — landing page #create-resume.
 *
 * Fully manual: every word comes from the candidate. There are no
 * suggestions, sample data or generated text. The form state is posted to
 * the server (career_app/create_resume.py), which validates it and returns
 * the arranged resume document; the live preview renders that document, and
 * the PDF is drawn from the same document, so preview and download match.
 *
 * Drafts: signed-in candidates save to their account (several resumes, each
 * only visible to its owner); visitors can save a draft on this device.
 */
(function () {
  'use strict';
  var app = document.getElementById('crApp');
  if (!app) return;

  var D = app.dataset;
  var AUTH = D.auth === '1';
  var LOCAL_KEY = 'cbCreateResume.v1.' + (D.uid || 'guest');
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var EMP = ['Full-time', 'Part-time', 'Internship', 'Contract', 'Freelance', 'Apprenticeship', 'Other'];
  var QUAL = ['PhD', "Master's Degree", "Bachelor's Degree", 'Diploma', 'Higher Secondary', 'Secondary School', 'Other'];
  var PTYPE = ['Academic Project', 'Personal Project', 'Professional Project', 'Internship Project', 'Research Project', 'Other'];
  var PROF = ['Basic', 'Conversational', 'Intermediate', 'Professional', 'Native'];
  var SUMMARY_LIMIT = 1200;
  var THIS_YEAR = new Date().getFullYear();

  var SECTIONS = [
    { key: 'personal', title: 'Personal Information', req: true },
    { key: 'summary', title: 'Professional Summary' },
    { key: 'experience', title: 'Work Experience' },
    { key: 'education', title: 'Education' },
    { key: 'skills', title: 'Skills' },
    { key: 'projects', title: 'Projects' },
    { key: 'certifications', title: 'Certifications & Training' },
    { key: 'achievements', title: 'Achievements & Awards' },
    { key: 'internships', title: 'Internships & Volunteering' },
    { key: 'languages', title: 'Languages & Additional Information' }
  ];
  var SECTION_OF = { volunteering: 'internships' };
  var SKILLS = [
    ['technical', 'Technical Skills', 'Programming languages, frameworks, databases, platforms and technologies.'],
    ['functional', 'Functional Skills', 'Industry knowledge, operations, business processes, project management, administration.'],
    ['soft', 'Soft Skills', 'Communication, teamwork, leadership, problem-solving, time management.'],
    ['tools', 'Tools & Technologies', 'Software applications, development tools, business systems and platforms.']
  ];
  var ADDITIONAL = [['memberships', 'Professional memberships'], ['publications', 'Publications'], ['research', 'Research'],
    ['activities', 'Extracurricular activities'], ['hobbies', 'Hobbies & interests'], ['other', 'Other relevant information']];

  var BLANK = {
    experience: { company: '', title: '', type: '', location: '', department: '', start_month: '', start_year: '', end_month: '', end_year: '', current: false, responsibilities: '', projects: '', achievements: '', tools: '' },
    education: { qualification: '', degree: '', specialization: '', institution: '', location: '', start_year: '', end_year: '', current: false, grade: '', coursework: '', achievements: '' },
    projects: { title: '', type: '', organization: '', start_month: '', start_year: '', end_month: '', end_year: '', current: false, overview: '', role: '', responsibilities: '', technologies: '', outcomes: '', url: '' },
    certifications: { name: '', issuer: '', issue_month: '', issue_year: '', exp_month: '', exp_year: '', credential_id: '', url: '', description: '' },
    achievements: { title: '', organization: '', month: '', year: '', description: '', url: '' },
    internships: { organization: '', title: '', location: '', start_month: '', start_year: '', end_month: '', end_year: '', current: false, responsibilities: '', projects: '', skills: '', achievements: '' },
    volunteering: { organization: '', role: '', location: '', start_month: '', start_year: '', end_month: '', end_year: '', current: false, responsibilities: '', contributions: '', achievements: '' },
    languages: { name: '', proficiency: '' }
  };
  var NOUN = { experience: 'Experience', education: 'Education', projects: 'Project', certifications: 'Certification',
    achievements: 'Achievement', internships: 'Internship', volunteering: 'Volunteering', languages: 'Language' };

  // Field definitions for the repeatable entries. '@x' entries are date groups.
  var LINES = ' (one point per line)';
  var FIELDS = {
    experience: [['company', 'Company name', { req: 1 }], ['title', 'Job title', { req: 1 }], ['type', 'Employment type', { select: EMP }],
      ['location', 'Location', { opt: 1, ph: 'City, Country' }], ['department', 'Department', { opt: 1 }], ['@dates', 'Currently working here'],
      ['responsibilities', 'Roles & responsibilities' + LINES, { area: 4, full: 1 }], ['projects', 'Projects handled' + LINES, { area: 2, full: 1, opt: 1 }],
      ['achievements', 'Key achievements' + LINES, { area: 2, full: 1, opt: 1 }], ['tools', 'Tools & technologies used', { full: 1, opt: 1, ph: 'Comma separated' }]],
    education: [['qualification', 'Qualification', { req: 1, select: QUAL }], ['degree', 'Degree', { opt: 1, ph: 'e.g. B.Tech, MBA' }],
      ['specialization', 'Specialization / major', { opt: 1 }], ['institution', 'Institution / university', { req: 1 }], ['location', 'College location', { opt: 1 }],
      ['@years', 'Currently studying'], ['grade', 'Grade / CGPA / percentage', { opt: 1 }], ['coursework', 'Relevant coursework', { full: 1, opt: 1 }],
      ['achievements', 'Academic achievements' + LINES, { area: 2, full: 1, opt: 1 }]],
    projects: [['title', 'Project title', { req: 1, full: 1 }], ['type', 'Project type', { select: PTYPE }], ['organization', 'Organisation / institution', { opt: 1 }],
      ['@dates', 'Ongoing project'], ['overview', 'Project overview', { area: 3, full: 1, opt: 1 }], ['role', 'Your role', { opt: 1 }],
      ['url', 'Project URL', { opt: 1, type: 'url', ph: 'https://' }], ['responsibilities', 'Responsibilities' + LINES, { area: 3, full: 1, opt: 1 }],
      ['technologies', 'Technologies / tools used', { full: 1, opt: 1 }], ['outcomes', 'Project outcomes' + LINES, { area: 2, full: 1, opt: 1 }]],
    certifications: [['name', 'Certification / course name', { req: 1, full: 1 }], ['issuer', 'Issuing organisation', { req: 1 }],
      ['credential_id', 'Credential ID', { opt: 1 }], ['@issue', 'Issue date'], ['@expiry', 'Expiration date'],
      ['url', 'Credential verification URL', { opt: 1, full: 1, type: 'url', ph: 'https://' }], ['description', 'Description', { area: 2, full: 1, opt: 1 }]],
    achievements: [['title', 'Achievement title', { req: 1, full: 1 }], ['organization', 'Organisation', { opt: 1 }], ['@when', 'Date'],
      ['description', 'Description', { area: 2, full: 1, opt: 1 }], ['url', 'Supporting URL', { opt: 1, full: 1, type: 'url', ph: 'https://' }]],
    internships: [['organization', 'Organisation', { req: 1 }], ['title', 'Internship title', { req: 1 }], ['location', 'Location', { opt: 1 }],
      ['@dates', 'Ongoing internship'], ['responsibilities', 'Responsibilities' + LINES, { area: 3, full: 1, opt: 1 }],
      ['projects', 'Projects' + LINES, { area: 2, full: 1, opt: 1 }], ['skills', 'Skills & tools used', { full: 1, opt: 1 }],
      ['achievements', 'Achievements' + LINES, { area: 2, full: 1, opt: 1 }]],
    volunteering: [['organization', 'Organisation', { req: 1 }], ['role', 'Role', { req: 1 }], ['location', 'Location', { opt: 1 }],
      ['@dates', 'Currently volunteering'], ['responsibilities', 'Responsibilities' + LINES, { area: 2, full: 1, opt: 1 }],
      ['contributions', 'Contributions' + LINES, { area: 2, full: 1, opt: 1 }], ['achievements', 'Achievements' + LINES, { area: 2, full: 1, opt: 1 }]]
  };

  // Hint text shown inside empty fields (format examples only — never filled in as values).
  var PLACEHOLDER = {
    'personal.name': 'e.g. Anita Sharma', 'personal.title': 'e.g. Project Manager', 'personal.email': 'e.g. you@example.com',
    'personal.phone': 'e.g. +91 98765 43210', 'personal.city': 'e.g. Hyderabad', 'personal.state': 'e.g. Telangana',
    'personal.country': 'e.g. India', 'personal.linkedin': 'e.g. linkedin.com/in/your-name', 'personal.github': 'e.g. github.com/your-name',
    'personal.portfolio': 'e.g. yourportfolio.com', 'personal.website': 'e.g. yourname.com', 'personal.profile_url': 'e.g. behance.net/your-name',
    'personal.address': 'e.g. Street, Area, City – PIN code',
    'summary': 'Describe your background, main areas of expertise, relevant experience, key strengths and career objective in 3–5 sentences.',
    'experience.company': 'e.g. ABC Infra Pvt Ltd', 'experience.title': 'e.g. Site Engineer', 'experience.department': 'e.g. Projects',
    'experience.responsibilities': 'e.g. Supervised daily site activities for a team of 20\nPrepared weekly progress reports',
    'experience.projects': 'e.g. G+12 residential tower, Hyderabad', 'experience.achievements': 'e.g. Completed handover two weeks ahead of schedule',
    'education.specialization': 'e.g. Civil Engineering', 'education.institution': 'e.g. JNTU Hyderabad', 'education.location': 'e.g. Hyderabad',
    'education.grade': 'e.g. CGPA 8.2 / 78%', 'education.coursework': 'e.g. Structural Analysis, Surveying', 'education.achievements': 'e.g. University rank 5 in final year',
    'projects.title': 'e.g. Construction Progress Tracker', 'projects.organization': 'e.g. JNTU Hyderabad', 'projects.role': 'e.g. Team lead',
    'projects.overview': 'e.g. A web dashboard to track daily site progress and material use.', 'projects.responsibilities': 'e.g. Designed the database schema\nBuilt the reporting module',
    'projects.technologies': 'e.g. Python, Django, MySQL', 'projects.outcomes': 'e.g. Reduced manual reporting time by 30%',
    'certifications.name': 'e.g. Project Management Professional (PMP)', 'certifications.issuer': 'e.g. PMI', 'certifications.credential_id': 'e.g. 1234567',
    'certifications.description': 'e.g. Covers planning, risk and stakeholder management',
    'achievements.title': 'e.g. Best Employee of the Year', 'achievements.organization': 'e.g. ABC Infra Pvt Ltd', 'achievements.description': 'e.g. Recognised for on-time project delivery',
    'internships.organization': 'e.g. XYZ Builders', 'internships.title': 'e.g. Civil Engineering Intern', 'internships.location': 'e.g. Pune',
    'internships.responsibilities': 'e.g. Assisted with site surveys and quantity calculations', 'internships.projects': 'e.g. Residential block foundation works',
    'internships.skills': 'e.g. AutoCAD, Total Station', 'internships.achievements': 'e.g. Received a pre-placement offer',
    'volunteering.organization': 'e.g. Habitat for Humanity', 'volunteering.role': 'e.g. Volunteer', 'volunteering.location': 'e.g. Chennai',
    'volunteering.responsibilities': 'e.g. Organised weekend build drives', 'volunteering.contributions': 'e.g. Helped build 3 homes', 'volunteering.achievements': 'e.g. Volunteer of the Month',
    'languages.name': 'e.g. English',
    'additional.memberships': 'e.g. Member, Institution of Engineers (India)', 'additional.publications': 'e.g. Paper title, Journal name, 2024',
    'additional.research': 'e.g. Study on low-cost building materials', 'additional.activities': 'e.g. Captain, college cricket team',
    'additional.hobbies': 'e.g. Photography, trekking', 'additional.other': 'e.g. Willing to relocate'
  };

  function empty() {
    return {
      template: 'classic',
      personal: { name: '', title: '', email: '', phone: '', city: '', state: '', country: '', linkedin: '', github: '', portfolio: '', website: '', profile_url: '', address: '' },
      summary: '', experience: [], education: [], skills: { technical: [], functional: [], soft: [], tools: [] }, projects: [],
      certifications: [], achievements: [], internships: [], volunteering: [], languages: [],
      additional: { memberships: '', publications: '', research: '', activities: '', hobbies: '', other: '' }, order: {}
    };
  }
  function copy(o) { return JSON.parse(JSON.stringify(o)); }
  function merge(data) {   // a loaded draft, completed with any fields it lacks
    var s = empty();
    if (!data || typeof data !== 'object') return s;
    Object.keys(s).forEach(function (k) {
      if (data[k] == null) return;
      if (Array.isArray(s[k])) s[k] = (data[k] || []).map(function (e) { return Object.assign(copy(BLANK[k]), e); });
      else if (typeof s[k] === 'object') s[k] = Object.assign(s[k], data[k]);
      else s[k] = data[k];
    });
    if (['classic', 'modern', 'minimal'].indexOf(s.template) < 0) s.template = 'classic';
    return s;
  }

  var S = empty();
  var openSec = 'personal', openEntry = {}, dirty = false, draftId = null, drafts = [];
  var lastErrors = [], lastStatus = {}, lastDoc = null, touched = {}, showAll = false;
  var zoom = 0, mode = 'live', pageImgs = [], pageIdx = 0, pvTimer = null, pvSeq = 0;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(sel, root) { return (root || app).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || app).querySelectorAll(sel)); }
  function csrf() { var i = document.querySelector('#crPrintForm [name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  function uid() { return Math.random().toString(36).slice(2, 9); }
  function get(path) {
    var o = S, parts = path.split('.');
    for (var i = 0; i < parts.length; i++) { if (o == null) return ''; o = o[parts[i]]; }
    return o == null ? '' : o;
  }
  function set(path, v) {
    var o = S, parts = path.split('.'), last = parts.pop();
    parts.forEach(function (p) { o = o[p]; });
    o[last] = v;
  }

  /* ───────────────────────── skeleton ───────────────────────── */
  function tplThumb(t) {
    var bar = t === 'modern' ? '<rect x="6" y="6" width="68" height="3" fill="#1d4ed8"/>' : t === 'minimal' ? '' : '<rect x="6" y="14" width="68" height="1" fill="#111"/>';
    var name = t === 'classic' ? '<rect x="22" y="8" width="36" height="4" rx="1" fill="#111"/>' : '<rect x="6" y="' + (t === 'modern' ? 12 : 8) + '" width="34" height="4" rx="1" fill="#1f2937"/>';
    var head = t === 'modern' ? '#1d4ed8' : t === 'minimal' ? '#9ca3af' : '#111';
    var lines = '';
    [24, 40].forEach(function (y) {
      lines += '<rect x="6" y="' + y + '" width="22" height="2.5" fill="' + head + '"/>' +
        (t !== 'minimal' ? '<rect x="6" y="' + (y + 4) + '" width="68" height=".6" fill="' + head + '"/>' : '') +
        '<rect x="6" y="' + (y + 7) + '" width="60" height="1.6" fill="#cbd5e1"/><rect x="6" y="' + (y + 10.5) + '" width="52" height="1.6" fill="#cbd5e1"/>';
    });
    return '<svg viewBox="0 0 80 56" aria-hidden="true">' + bar + name + lines + '</svg>';
  }

  app.innerHTML =
    '<div class="cr-top">' +
      '<div class="cr-tpls" role="group" aria-label="Resume template">' +
        ['classic', 'modern', 'minimal'].map(function (t) {
          return '<button type="button" class="cr-tpl" data-act="tpl" data-t="' + t + '" aria-pressed="false">' + tplThumb(t) + t.charAt(0).toUpperCase() + t.slice(1) + '</button>';
        }).join('') +
      '</div>' +
      '<div><div class="cr-drafts">' +
        (AUTH ? '<label class="cr-sr" for="crDraftSel">My resumes</label><select id="crDraftSel" aria-label="My resumes"></select>' : '') +
        '<button type="button" class="cr-btn" data-act="new">New resume</button>' +
        '<button type="button" class="cr-btn primary" data-act="save">Save Draft</button>' +
        (AUTH ? '<button type="button" class="cr-btn danger" data-act="delete" id="crDel" disabled>Delete</button>' : '') +
      '</div><div class="cr-status" id="crStatus" aria-live="polite">' +
        (AUTH ? '' : 'Drafts are saved on this device. <a href="' + esc(D.login) + '">Sign in</a> to save resumes to your account.') + '</div></div>' +
    '</div>' +
    '<div class="cr-grid">' +
      '<div class="cr-form" id="crForm">' +
        '<div class="cr-progress"><div class="cr-progress-h">Resume progress <span id="crProgTxt"></span></div>' +
          '<div class="cr-bar"><i id="crProgBar" style="width:0"></i></div><nav class="cr-chips-nav" id="crNav" aria-label="Resume sections"></nav></div>' +
        '<div id="crSecs"></div>' +
      '</div>' +
      '<aside class="cr-preview" id="crPreview" aria-label="Resume preview">' +
        '<div class="cr-pv-bar">' +
          '<span class="grp"><button type="button" class="cr-ib" data-act="zoom-out" aria-label="Zoom out">−</button><span class="lbl" id="crZoom">100%</span>' +
          '<button type="button" class="cr-ib" data-act="zoom-in" aria-label="Zoom in">+</button><button type="button" class="cr-btn sm" data-act="zoom-fit">Fit</button></span>' +
          '<span class="grp"><button type="button" class="cr-ib" data-act="page-prev" aria-label="Previous page">‹</button><span class="lbl" id="crPage">1 / 1</span>' +
          '<button type="button" class="cr-ib" data-act="page-next" aria-label="Next page">›</button></span><span class="sp"></span>' +
          '<button type="button" class="cr-btn sm" data-act="edit">Edit Details</button>' +
          '<button type="button" class="cr-btn sm" data-act="print-preview" id="crPPBtn">Print Preview</button>' +
          '<button type="button" class="cr-btn sm" data-act="print">Print</button>' +
          '<button type="button" class="cr-btn sm primary" data-act="pdf">Download PDF</button>' +
        '</div>' +
        '<div class="cr-pv-mode" id="crMode"></div>' +
        '<div class="cr-pv-view" id="crView" tabindex="0"><div class="cr-pv-zoom" id="crZoomBox"></div></div>' +
      '</aside>' +
    '</div>';

  /* ───────────────────────── field helpers ───────────────────────── */
  function fid(p) { return 'cr_' + p.replace(/[^a-z0-9]/gi, '_'); }
  function mark(o) { return o.req ? ' <span class="req" aria-hidden="true">*</span>' : (o.opt ? ' <span class="opt">(optional)</span>' : ''); }
  function fld(path, label, o) {
    o = o || {};
    if (!o.ph && !o.select) o = Object.assign({ ph: PLACEHOLDER[path.replace(/\.\d+\./, '.')] }, o);
    var v = get(path), id = fid(path), a = ' id="' + id + '" data-k="' + path + '" aria-describedby="' + id + '_m"' + (o.req ? ' aria-required="true"' : '') + (o.dis ? ' disabled' : '');
    var input;
    if (o.select) {
      input = '<select' + a + '><option value="">' + (o.req ? 'Select…' : '—') + '</option>' + o.select.map(function (x) {
        var val = Array.isArray(x) ? x[0] : x, txt = Array.isArray(x) ? x[1] : x;
        return '<option value="' + esc(val) + '"' + (String(val) === String(v) ? ' selected' : '') + '>' + esc(txt) + '</option>';
      }).join('') + '</select>';
    } else if (o.area) {
      input = '<textarea' + a + ' rows="' + o.area + '" maxlength="' + (o.max || 2000) + '"' + (o.ph ? ' placeholder="' + esc(o.ph) + '"' : '') + '>' + esc(v) + '</textarea>';
    } else {
      input = '<input' + a + ' type="' + (o.type || 'text') + '" value="' + esc(v) + '" maxlength="' + (o.max || 300) + '"' +
        (o.ph ? ' placeholder="' + esc(o.ph) + '"' : '') + (o.ac ? ' autocomplete="' + o.ac + '"' : '') + '>';
    }
    return '<div class="cr-f' + (o.full ? ' full' : '') + '"><label for="' + id + '">' + esc(label) + mark(o) + '</label>' + input +
      (o.count ? '<span class="cr-count" id="' + id + '_c"></span>' : '') + '<span class="cr-msg" id="' + id + '_m" data-msg="' + path + '"></span></div>';
  }
  function years(future) {
    var out = [], top = THIS_YEAR + (future ? 8 : 0);
    for (var y = top; y >= 1960; y--) out.push(String(y));
    return out;
  }
  var MONTH_OPTS = MONTHS.map(function (m, i) { return [String(i + 1), m]; });
  function monthYear(base, mKey, yKey, label, o) {
    o = o || {};
    return '<div class="cr-f"><label for="' + fid(base + mKey) + '">' + esc(label) + mark(o) + '</label><div class="cr-pair">' +
      fld(base + mKey, 'Month', { select: MONTH_OPTS, dis: o.dis }).replace('<label', '<label class="cr-sr"') +
      fld(base + yKey, 'Year', { select: years(o.future), dis: o.dis }).replace('<label', '<label class="cr-sr"') + '</div></div>';
  }
  function checkbox(path, label) {
    return '<label class="cr-check"><input type="checkbox" data-k="' + path + '" data-bool="1"' + (get(path) ? ' checked' : '') + '> ' + esc(label) + '</label>';
  }

  /* ───────────────────────── entries ───────────────────────── */
  function entryTitle(kind, e) {
    var parts = {
      experience: [e.title, e.company], education: [e.degree || e.qualification, e.institution], projects: [e.title, e.type],
      certifications: [e.name, e.issuer], achievements: [e.title, e.organization], internships: [e.title, e.organization],
      volunteering: [e.role, e.organization]
    }[kind] || [];
    var main = parts.filter(Boolean).join(' · ');
    var when = e.current ? 'Present' : (e.end_year || e.year || e.issue_year || '');
    if (e.start_year && when) when = e.start_year + ' – ' + when;
    return main ? esc(main) + (when ? ' <em>(' + esc(when) + ')</em>' : '') : '<em>New ' + NOUN[kind].toLowerCase() + ' — not filled in yet</em>';
  }
  function entryBody(kind, i) {
    var base = kind + '.' + i + '.', e = S[kind][i], h = '';
    FIELDS[kind].forEach(function (f) {
      var key = f[0];
      if (key === '@dates') {
        h += monthYear(base, 'start_month', 'start_year', 'Start date', { req: kind === 'experience' }) +
          monthYear(base, 'end_month', 'end_year', 'End date', { dis: !!e.current }) +
          '<div class="cr-f full">' + checkbox(base + 'current', f[1]) + '</div>';
      } else if (key === '@years') {
        h += fld(base + 'start_year', 'Start year', { select: years(false), opt: 1 }) +
          fld(base + 'end_year', e.current ? 'Expected graduation year' : 'Graduation year', { select: years(true), opt: 1 }) +
          '<div class="cr-f full">' + checkbox(base + 'current', f[1]) + '</div>';
      } else if (key === '@issue') {
        h += monthYear(base, 'issue_month', 'issue_year', f[1], { opt: 1 });
      } else if (key === '@expiry') {
        h += monthYear(base, 'exp_month', 'exp_year', f[1], { opt: 1, future: true });
      } else if (key === '@when') {
        h += monthYear(base, 'month', 'year', f[1], { opt: 1 });
      } else {
        h += fld(base + key, f[1], f[2]);
      }
    });
    return '<div class="cr-fields">' + h + '</div>';
  }
  function entryList(kind) {
    var list = S[kind], h = '';
    list.forEach(function (e, i) {
      if (!e._id) e._id = uid();
      var open = !!openEntry[e._id];
      h += '<div class="cr-entry" data-entry="' + kind + '.' + i + '">' +
        '<div class="cr-entry-h"><span class="t">' + entryTitle(kind, e) + '</span>' +
        '<button type="button" class="cr-btn sm" data-act="toggle" data-kind="' + kind + '" data-i="' + i + '" aria-expanded="' + open + '">' + (open ? 'Done' : 'Edit') + '</button>' +
        '<button type="button" class="cr-ib" data-act="up" data-kind="' + kind + '" data-i="' + i + '" aria-label="Move up"' + (i === 0 ? ' disabled' : '') + '>↑</button>' +
        '<button type="button" class="cr-ib" data-act="down" data-kind="' + kind + '" data-i="' + i + '" aria-label="Move down"' + (i === list.length - 1 ? ' disabled' : '') + '>↓</button>' +
        '<button type="button" class="cr-ib del" data-act="remove" data-kind="' + kind + '" data-i="' + i + '" aria-label="Remove ' + NOUN[kind].toLowerCase() + ' ' + (i + 1) + '">✕</button></div>' +
        (open ? '<div class="cr-entry-b">' + entryBody(kind, i) + '</div>' : '') + '</div>';
    });
    var auto = (S.order[kind] || 'auto') !== 'manual';
    var order = list.length > 1 ? '<div class="cr-order">' + (auto ? 'Shown newest first in your resume.' :
      'Shown in your order. <button type="button" data-act="auto-order" data-kind="' + kind + '">Sort newest first</button>') + '</div>' : '';
    return '<div data-list="' + kind + '">' + h + order + '<button type="button" class="cr-add" data-act="add" data-kind="' + kind + '">+ ' +
      (list.length ? 'Add another ' + NOUN[kind].toLowerCase() : 'Add ' + NOUN[kind].toLowerCase()) + '</button></div>';
  }

  /* ───────────────────────── sections ───────────────────────── */
  function body(key) {
    switch (key) {
      case 'personal':
        return '<div class="cr-fields">' +
          fld('personal.name', 'Full name', { req: 1, ac: 'name', max: 100 }) +
          fld('personal.title', 'Professional title / target role', { req: 1, max: 100 }) +
          fld('personal.email', 'Email address', { req: 1, type: 'email', ac: 'email', max: 120 }) +
          fld('personal.phone', 'Contact number', { req: 1, type: 'tel', ac: 'tel', max: 40 }) +
          fld('personal.city', 'Current city', { req: 1, ac: 'address-level2', max: 80 }) +
          fld('personal.state', 'State', { req: 1, ac: 'address-level1', max: 80 }) +
          fld('personal.country', 'Country', { req: 1, ac: 'country-name', max: 80 }) +
          fld('personal.linkedin', 'LinkedIn profile URL', { opt: 1, type: 'url' }) +
          fld('personal.github', 'GitHub profile URL', { opt: 1, type: 'url' }) +
          fld('personal.portfolio', 'Portfolio website', { opt: 1, type: 'url' }) +
          fld('personal.website', 'Personal website', { opt: 1, type: 'url' }) +
          fld('personal.profile_url', 'Professional profile URL', { opt: 1, type: 'url' }) +
          fld('personal.address', 'Address (only if you want it on your resume)', { opt: 1, full: 1, max: 160 }) + '</div>';
      case 'summary':
        return '<p class="cr-help">Write in your own words: your background, main areas of expertise, relevant experience, key strengths and, if you like, your career objective.</p>' +
          '<div class="cr-fields">' + fld('summary', 'Professional summary', { full: 1, area: 7, max: SUMMARY_LIMIT, count: 1 }) + '</div>';
      case 'experience':
        return '<p class="cr-help">Optional — freshers can leave this empty. Add each role separately; tick “Currently working here” for your present job.</p>' + entryList('experience');
      case 'education':
        return '<p class="cr-help">Add each qualification. Grade, coursework and achievements are optional.</p>' + entryList('education');
      case 'skills':
        return '<p class="cr-help">Type skills one at a time, or several separated by commas. Use the arrows to reorder and ✎ to edit.</p>' +
          SKILLS.map(function (s) {
            return '<div class="cr-skill" data-skill="' + s[0] + '"><b>' + esc(s[1]) + '</b><small>' + esc(s[2]) + '</small><ul class="cr-sk-list">' +
              S.skills[s[0]].map(function (x, i) {
                return '<li data-i="' + i + '"><span>' + esc(x) + '</span>' +
                  '<button type="button" data-act="sk-edit" data-cat="' + s[0] + '" data-i="' + i + '" aria-label="Edit ' + esc(x) + '">✎</button>' +
                  '<button type="button" data-act="sk-left" data-cat="' + s[0] + '" data-i="' + i + '" aria-label="Move ' + esc(x) + ' earlier"' + (i === 0 ? ' disabled' : '') + '>←</button>' +
                  '<button type="button" data-act="sk-right" data-cat="' + s[0] + '" data-i="' + i + '" aria-label="Move ' + esc(x) + ' later"' + (i === S.skills[s[0]].length - 1 ? ' disabled' : '') + '>→</button>' +
                  '<button type="button" data-act="sk-del" data-cat="' + s[0] + '" data-i="' + i + '" aria-label="Remove ' + esc(x) + '">✕</button></li>';
              }).join('') + '</ul><div class="cr-sk-add"><input type="text" data-skadd="' + s[0] + '" placeholder="Add a skill (or several, comma separated)" aria-label="Add ' + esc(s[1]) + '" maxlength="300">' +
              '<button type="button" class="cr-btn sm" data-act="sk-add" data-cat="' + s[0] + '">Add skill</button></div></div>';
          }).join('');
      case 'projects':
        return '<p class="cr-help">Academic, personal, professional, internship or research projects. Latest first by default.</p>' + entryList('projects');
      case 'certifications':
        return '<p class="cr-help">Certifications, professional training and workshops you have completed.</p>' + entryList('certifications');
      case 'achievements':
        return '<p class="cr-help">Awards, recognitions, academic accomplishments, competition results and professional milestones.</p>' + entryList('achievements');
      case 'internships':
        return '<p class="cr-help">Both optional — they only appear on your resume when filled in.</p><h4 class="cr-sub">Internships</h4>' +
          entryList('internships') + '<h4 class="cr-sub">Volunteering</h4>' + entryList('volunteering');
      case 'languages':
        var langs = S.languages.map(function (l, i) {
          return '<div class="cr-entry"><div class="cr-entry-b" style="border:0;border-radius:12px"><div class="cr-fields">' +
            fld('languages.' + i + '.name', 'Language', { req: 1, max: 60 }) + fld('languages.' + i + '.proficiency', 'Proficiency', { select: PROF }) +
            '</div><div class="cr-order" style="justify-content:flex-end">' +
            '<button type="button" class="cr-ib" data-act="up" data-kind="languages" data-i="' + i + '" aria-label="Move up"' + (i === 0 ? ' disabled' : '') + '>↑</button>' +
            '<button type="button" class="cr-ib" data-act="down" data-kind="languages" data-i="' + i + '" aria-label="Move down"' + (i === S.languages.length - 1 ? ' disabled' : '') + '>↓</button>' +
            '<button type="button" class="cr-ib del" data-act="remove" data-kind="languages" data-i="' + i + '" aria-label="Remove language ' + (i + 1) + '">✕</button></div></div></div>';
        }).join('');
        return '<p class="cr-help">All optional. Empty items never appear on your resume.</p><h4 class="cr-sub">Languages</h4>' + langs +
          '<button type="button" class="cr-add" data-act="add" data-kind="languages">+ Add language</button>' +
          '<h4 class="cr-sub">Additional information</h4><div class="cr-fields">' +
          ADDITIONAL.map(function (a) { return fld('additional.' + a[0], a[1] + LINES, { area: 2, full: 1, opt: 1 }); }).join('') + '</div>';
    }
    return '';
  }
  function sectionHTML(sec, n) {
    var open = openSec === sec.key, st = lastStatus[sec.key] || 'empty';
    return '<div role="region" aria-label="' + esc(sec.title) + '" class="cr-sec ' + st + '" id="cr-sec-' + sec.key + '" data-sec="' + sec.key + '">' +
      '<button type="button" class="cr-sec-h" data-act="sec" data-sec="' + sec.key + '" aria-expanded="' + open + '" aria-controls="cr-b-' + sec.key + '">' +
      '<span class="n">' + (st === 'complete' ? '✓' : st === 'error' ? '!' : n) + '</span><b>' + esc(sec.title) + '</b>' +
      '<span class="cr-tag' + (sec.req ? ' req' : '') + '">' + (sec.req ? 'Required' : 'Optional') + '</span><span class="chev" aria-hidden="true">▾</span></button>' +
      '<div class="cr-sec-b" id="cr-b-' + sec.key + '"' + (open ? '' : ' hidden') + '>' + (open ? body(sec.key) : '') +
      '<div class="cr-sec-foot"><button type="button" class="cr-btn sm danger" data-act="reset" data-sec="' + sec.key + '">Reset section</button><span>' +
      (n > 1 ? '<button type="button" class="cr-btn sm" data-act="go" data-sec="' + SECTIONS[n - 2].key + '">‹ Previous</button> ' : '') +
      (n < SECTIONS.length ? '<button type="button" class="cr-btn sm primary" data-act="go" data-sec="' + SECTIONS[n].key + '">Next section ›</button>' :
        '<button type="button" class="cr-btn sm primary" data-act="show-preview">Preview Resume</button>') +
      '</span></div></div></div>';
  }
  function renderForm() {
    var a = document.activeElement, keep = a && app.contains(a) ? (a.getAttribute('data-k') || a.getAttribute('data-skadd')) : null;
    $('#crSecs').innerHTML = SECTIONS.map(function (s, i) { return sectionHTML(s, i + 1); }).join('');
    if (keep) { var el = $('[data-k="' + keep + '"],[data-skadd="' + keep + '"]'); if (el) el.focus({ preventScroll: true }); }
    $$('[data-act="tpl"]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.t === S.template)); });
    updateCounter(); applyStatus();
  }
  function updateCounter() {
    var c = document.getElementById(fid('summary') + '_c');
    if (c) { var n = S.summary.length; c.textContent = n + ' / ' + SUMMARY_LIMIT + ' characters'; c.classList.toggle('near', n > SUMMARY_LIMIT * 0.9); }
  }

  /* ───────────────────────── status, progress & messages ───────────────────────── */
  function applyStatus() {
    var done = SECTIONS.filter(function (s) { return lastStatus[s.key] === 'complete'; }).length;
    $('#crProgTxt').textContent = done + ' of ' + SECTIONS.length + ' sections filled';
    $('#crProgBar').style.width = Math.round(done / SECTIONS.length * 100) + '%';
    $('#crNav').innerHTML = SECTIONS.map(function (s, i) {
      var st = lastStatus[s.key] || 'empty';
      return '<button type="button" class="' + st + '" data-act="go" data-sec="' + s.key + '"' + (openSec === s.key ? ' aria-current="true"' : '') + '><i></i>' + (i + 1) + '. ' + esc(s.title) + '</button>';
    }).join('');
    SECTIONS.forEach(function (s, i) {
      var sec = document.getElementById('cr-sec-' + s.key); if (!sec) return;
      var st = lastStatus[s.key] || 'empty';
      sec.className = 'cr-sec ' + st;
      var n = $('.cr-sec-h .n', sec); if (n) n.textContent = st === 'complete' ? '✓' : st === 'error' ? '!' : String(i + 1);
    });
    var by = {};
    lastErrors.forEach(function (e) { if (!by[e.field]) by[e.field] = e.message; });
    $$('[data-msg]').forEach(function (m) {
      var f = m.getAttribute('data-msg'), msg = (showAll || touched[f]) ? (by[f] || '') : '';
      m.textContent = msg;
      var w = m.closest('.cr-f'); if (w) w.classList.toggle('invalid', !!msg);
      var input = w && w.querySelector('[data-k]');
      if (input) { if (msg) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid'); }
    });
  }

  /* ───────────────────────── preview ───────────────────────── */
  function schedulePreview(now) {
    clearTimeout(pvTimer);
    pvTimer = setTimeout(requestPreview, now ? 0 : 350);
  }
  function post(url, data) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(data) });
  }
  function requestPreview() {
    var seq = ++pvSeq;
    return post(D.preview, S).then(function (r) { return r.json(); }).then(function (d) {
      if (seq !== pvSeq || !d.ok) return d;
      lastDoc = d.document; lastErrors = d.errors || []; lastStatus = d.status || {};
      applyStatus();
      if (mode === 'live') renderLive();
      return d;
    }).catch(function () { status('Preview could not be updated — check your connection.', 'err'); });
  }
  function rich(t) { return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'); }
  function link(l) { return '<a href="' + esc(l.href) + '" target="_blank" rel="noopener">' + esc(l.text) + '</a>'; }
  function ul(items) { return items && items.length ? '<ul>' + items.map(function (b) { return '<li>' + rich(b) + '</li>'; }).join('') + '</ul>' : ''; }
  // Mirrors career_app/create_resume_pdf.py so the preview matches the PDF.
  function docHTML(d) {
    var hasContent = d.name || d.title || (d.sections || []).length;
    if (!hasContent) return '<div class="crp ' + d.template + '"><p class="crp-empty">Your resume preview appears here as you fill in the form.</p></div>';
    var h = '<div class="crp ' + d.template + '" id="crDoc"><div class="crp-hdr"><h1>' + esc(d.name || 'Your Name') + '</h1>' +
      (d.title ? '<p class="crp-title">' + esc(d.title) + '</p>' : '');
    if (d.contact && d.contact.length) h += '<p class="crp-contact">' + d.contact.map(function (c) { return c.href ? link(c) : esc(c.text); }).join(' | ') + '</p>';
    if (d.links && d.links.length) h += '<p class="crp-contact">' + d.links.map(link).join(' | ') + '</p>';
    if (d.address) h += '<p class="crp-contact">' + esc(d.address) + '</p>';
    h += '</div>';
    (d.sections || []).forEach(function (s) {
      h += '<div class="crp-sec"><h2>' + esc(s.heading) + '</h2>';
      if (s.kind === 'text') h += s.text.split('\n').filter(function (x) { return x.trim(); }).map(function (x) { return '<p class="crp-j">' + rich(x) + '</p>'; }).join('');
      else if (s.kind === 'lines') h += s.items.map(function (i) { return '<p><b>' + esc(i.label) + ':</b> ' + esc(i.text) + '</p>'; }).join('');
      else if (s.kind === 'items') h += '<ul>' + s.items.map(function (i) {
        return '<li class="crp-j"><b>' + esc(i.title) + '</b>' + (i.text ? ' – ' + esc(i.text) : '') + (i.link && i.link.href ? ' | ' + link(i.link) : '') +
          (i.detail ? '<div class="crp-detail">' + rich(i.detail) + '</div>' : '') + '</li>';
      }).join('') + '</ul>';
      else if (s.kind === 'entries') h += s.items.map(function (i) {
        var notes = i.notes || [], role = notes.filter(function (n) { return n.label === 'Role'; });
        return '<div class="crp-e"><div class="crp-eh"><b>' + esc(i.title) + '</b>' + (i.subtitle ? ' &nbsp;|&nbsp; ' + esc(i.subtitle) : '') + '</div>' +
          (i.meta ? '<div class="crp-meta">' + esc(i.meta) + '</div>' : '') +
          (i.link && i.link.href ? '<div class="crp-meta">' + link(i.link) + '</div>' : '') +
          (i.paragraphs || []).map(function (p) { return '<p class="crp-j">' + rich(p) + '</p>'; }).join('') +
          role.map(function (n) { return '<p class="crp-role"><b>Role:</b> ' + esc(n.text) + '</p>'; }).join('') +
          ul(i.bullets) + (i.groups || []).map(function (g) { return '<p class="crp-g">' + esc(g.label) + ':</p>' + ul(g.bullets); }).join('') +
          notes.filter(function (n) { return n.label !== 'Role'; }).map(function (n) { return '<p class="crp-note">' + esc(n.label) + ': ' + esc(n.text) + '</p>'; }).join('') + '</div>';
      }).join('');
      h += '</div>';
    });
    return h + '</div>';
  }
  var PAGE_H = 1123;   // A4 at 794px wide
  function renderLive() {
    if (!lastDoc) return;
    $('#crZoomBox').innerHTML = docHTML(lastDoc);
    var doc = document.getElementById('crDoc');
    var pages = 1;
    if (doc) {
      pages = Math.max(1, Math.ceil(doc.scrollHeight / PAGE_H));
      doc.style.minHeight = (pages * PAGE_H) + 'px';
      for (var p = 1; p < pages; p++) {
        var b = document.createElement('div'); b.className = 'crp-break'; b.style.top = (p * PAGE_H) + 'px';
        b.innerHTML = '<span>Page ' + (p + 1) + '</span>'; doc.appendChild(b);
      }
    }
    $('#crMode').textContent = 'Live preview · ' + cap(lastDoc.template) + ' template · approximately ' + pages + (pages > 1 ? ' pages' : ' page') +
      '. Print Preview shows the exact PDF pages.';
    pageCount = pages; pageIdx = Math.min(pageIdx, pages - 1); updatePageLabel(); applyZoom();
  }
  var pageCount = 1;
  function cap(s) { return String(s || '').charAt(0).toUpperCase() + String(s || '').slice(1); }
  function updatePageLabel() {
    var total = mode === 'pages' ? pageImgs.length : pageCount;
    $('#crPage').textContent = (pageIdx + 1) + ' / ' + total;
    $('[data-act="page-prev"]').disabled = pageIdx <= 0;
    $('[data-act="page-next"]').disabled = pageIdx >= total - 1;
  }
  function topIn(view, el) { return el.getBoundingClientRect().top - view.getBoundingClientRect().top + view.scrollTop; }
  function fitZoom() { var w = $('#crView').clientWidth - 32; return Math.max(0.3, Math.min(1.5, w / 794)); }
  function applyZoom() {
    var z = zoom || fitZoom();
    $('#crZoomBox').style.zoom = z;
    $('#crZoom').textContent = Math.round(z * 100) + '%';
  }
  function goPage(i) {
    var total = mode === 'pages' ? pageImgs.length : pageCount;
    pageIdx = Math.max(0, Math.min(total - 1, i)); updatePageLabel();
    var z = zoom || fitZoom(), view = $('#crView');
    if (mode === 'pages') { var fig = $$('.cr-pv-pages figure')[pageIdx]; if (fig) view.scrollTo({ top: topIn(view, fig) - 16, behavior: 'smooth' }); }
    else view.scrollTo({ top: pageIdx * PAGE_H * z, behavior: 'smooth' });
  }
  $('#crView').addEventListener('scroll', function () {
    var view = $('#crView'), z = zoom || fitZoom(), i;
    if (mode === 'pages') {
      var figs = $$('.cr-pv-pages figure'); i = 0;
      figs.forEach(function (f, k) { if (topIn(view, f) - 40 <= view.scrollTop) i = k; });
    } else i = Math.floor((view.scrollTop + 40) / (PAGE_H * z));
    if (i !== pageIdx) { pageIdx = Math.max(0, i); updatePageLabel(); }
  });
  window.addEventListener('resize', function () { if (!zoom) applyZoom(); });

  /* ───────────────────────── actions ───────────────────────── */
  function status(msg, kind) { var s = document.getElementById('crStatus'); s.className = 'cr-status' + (kind ? ' ' + kind : ''); s.innerHTML = msg; }
  function changed() { dirty = true; schedulePreview(); }
  function openSection(key, scroll) {
    openSec = key; renderForm();
    if (scroll) { var sec = document.getElementById('cr-sec-' + key); if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  }
  function goToError(err) {
    var section = err.section || SECTION_OF[err.field.split('.')[0]] || err.field.split('.')[0];
    var parts = err.field.split('.');
    if (parts.length > 2 && S[parts[0]] && S[parts[0]][+parts[1]]) openEntry[S[parts[0]][+parts[1]]._id] = true;
    openSection(section, false);
    var el = $('[data-k="' + err.field + '"]') || document.getElementById('cr-sec-' + section);
    var box = el.closest('.cr-f') || el;
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    try { el.focus({ preventScroll: true }); } catch (e) {}
    box.classList.remove('cr-hl'); void box.offsetWidth; box.classList.add('cr-hl');
  }
  function ensureValid() {
    clearTimeout(pvTimer);
    return requestPreview().then(function () {
      if (!lastErrors.length) return true;
      showAll = true; applyStatus();
      status('Please fix ' + lastErrors.length + (lastErrors.length > 1 ? ' items' : ' item') + ' before downloading: ' + esc(lastErrors[0].message), 'err');
      goToError(lastErrors[0]);
      return false;
    });
  }
  function downloadPdf(btn) {
    ensureValid().then(function (ok) {
      if (!ok) return;
      btn.disabled = true; var label = btn.textContent; btn.textContent = 'Generating PDF…';
      post(D.pdf, S).then(function (r) {
        var ct = r.headers.get('Content-Type') || '';
        if (r.ok && ct.indexOf('application/pdf') > -1) return r.blob().then(function (blob) {
          var name = r.headers.get('X-Resume-Filename') || 'Resume.pdf', url = URL.createObjectURL(blob), a = document.createElement('a');
          a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
          status('Downloaded <b>' + esc(name) + '</b>.', 'ok');
        });
        return r.json().then(function (d) { status(esc(((d.errors || [])[0] || {}).message || 'The PDF could not be generated.'), 'err'); });
      }).catch(function () { status('The PDF could not be generated. Please check your connection and try again.', 'err'); })
        .then(function () { btn.disabled = false; btn.textContent = label; });
    });
  }
  function printPdf() {
    ensureValid().then(function (ok) {
      if (!ok) return;
      var f = document.getElementById('crPrintForm'); f.payload.value = JSON.stringify(S); f.submit();
      status('Your resume PDF opened in a new tab — use the print button there. (Allow pop-ups if nothing opened.)', 'ok');
    });
  }
  function printPreview(btn) {
    if (mode === 'pages') { mode = 'live'; btn.textContent = 'Print Preview'; pageIdx = 0; renderLive(); return; }
    ensureValid().then(function (ok) {
      if (!ok) return;
      btn.disabled = true; btn.textContent = 'Rendering…';
      post(D.pages, S).then(function (r) { return r.json(); }).then(function (d) {
        if (!d.ok) { status(esc(((d.errors || [])[0] || {}).message || 'Print preview is unavailable.'), 'err'); return; }
        mode = 'pages'; pageImgs = d.pages; pageIdx = 0;
        $('#crZoomBox').innerHTML = '<div class="cr-pv-pages">' + d.pages.map(function (src, i) {
          return '<figure><img src="' + src + '" alt="Resume page ' + (i + 1) + ' of ' + d.total + '"><figcaption>Page ' + (i + 1) + ' of ' + d.total + '</figcaption></figure>';
        }).join('') + '</div>';
        $('#crMode').textContent = 'Print preview · exactly what the PDF will look like (' + d.total + (d.total > 1 ? ' pages' : ' page') + ').';
        btn.textContent = 'Back to Live Preview'; updatePageLabel(); applyZoom(); $('#crView').scrollTop = 0;
      }).catch(function () { status('Print preview is unavailable right now.', 'err'); })
        .then(function () { btn.disabled = false; if (mode !== 'pages') btn.textContent = 'Print Preview'; });
    });
  }

  /* drafts */
  function draftSelect() {
    var sel = document.getElementById('crDraftSel'); if (!sel) return;
    sel.innerHTML = '<option value="">' + (drafts.length ? '— My resumes (' + drafts.length + ') —' : 'No saved resumes yet') + '</option>' +
      drafts.map(function (d) { return '<option value="' + d.id + '"' + (d.id === draftId ? ' selected' : '') + '>' + esc(d.title) + '</option>'; }).join('');
    var del = document.getElementById('crDel'); if (del) del.disabled = !draftId;
  }
  function loadDrafts() {
    return fetch(D.drafts, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
      drafts = (d && d.drafts) || []; draftSelect(); return drafts;
    }).catch(function () { return []; });
  }
  function loadDraft(id) {
    return fetch(D.draft.replace('/0/', '/' + id + '/'), { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { status('That resume could not be opened.', 'err'); return; }
      useState(merge(d.data)); draftId = d.draft.id; draftSelect();
      status('Opened “' + esc(d.draft.title) + '”.', 'ok');
    });
  }
  function useState(s) {
    S = s; dirty = false; touched = {}; showAll = false; openEntry = {}; openSec = 'personal'; mode = 'live';
    var pp = document.getElementById('crPPBtn'); if (pp) pp.textContent = 'Print Preview';
    renderForm(); schedulePreview(true);
  }
  function saveDraft(btn) {
    if (!AUTH) {
      try { localStorage.setItem(LOCAL_KEY, JSON.stringify(S)); dirty = false; status('Draft saved on this device. <a href="' + esc(D.login) + '">Sign in</a> to save it to your account.', 'ok'); }
      catch (e) { status('This browser blocked saving. Download the PDF to keep your resume.', 'err'); }
      return;
    }
    btn.disabled = true;
    post(D.save, { id: draftId, data: S }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { status(esc(((d.errors || [])[0] || {}).message || 'The draft could not be saved.'), 'err'); return; }
      draftId = d.draft.id; dirty = false; status('Saved “' + esc(d.draft.title) + '” to your account.', 'ok');
      return loadDrafts();
    }).catch(function () { status('The draft could not be saved. Please check your connection.', 'err'); })
      .then(function () { btn.disabled = false; });
  }
  function confirmDiscard() { return !dirty || window.confirm('You have unsaved changes. Discard them?'); }

  /* skills */
  function addSkills(cat) {
    var input = $('[data-skadd="' + cat + '"]'), list = S.skills[cat];
    var lower = list.map(function (x) { return x.toLowerCase(); });
    input.value.split(/[,\n;]/).map(function (x) { return x.trim().slice(0, 80); }).filter(Boolean).forEach(function (x) {
      if (lower.indexOf(x.toLowerCase()) < 0 && list.length < 40) { list.push(x); lower.push(x.toLowerCase()); }
    });
    input.value = ''; changed(); renderForm();
    var again = $('[data-skadd="' + cat + '"]'); if (again) again.focus();
  }
  function editSkill(cat, i) {
    var li = $('[data-skill="' + cat + '"] li[data-i="' + i + '"]'); if (!li) return;
    li.innerHTML = '<input type="text" data-skedit="' + cat + '" data-i="' + i + '" value="' + esc(S.skills[cat][i]) + '" aria-label="Edit skill" maxlength="80">';
    var inp = li.querySelector('input'); inp.focus(); inp.select();
  }
  function commitSkill(inp, cancel) {
    if (inp._done) return;
    inp._done = true;
    var cat = inp.dataset.skedit, i = +inp.dataset.i, v = inp.value.trim();
    if (!cancel) { if (v) S.skills[cat][i] = v; else S.skills[cat].splice(i, 1); changed(); }
    renderForm();
  }

  app.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act]'); if (!b || !app.contains(b)) return;
    var act = b.dataset.act, kind = b.dataset.kind, i = +b.dataset.i, list = kind ? S[kind] : null;
    switch (act) {
      case 'tpl': S.template = b.dataset.t; changed(); renderForm();
        if (mode === 'pages') { mode = 'live'; document.getElementById('crPPBtn').textContent = 'Print Preview'; }
        schedulePreview(true); break;
      case 'sec': openSection(openSec === b.dataset.sec ? '' : b.dataset.sec, false); break;
      case 'go': openSection(b.dataset.sec, true); break;
      case 'add':
        var n = copy(BLANK[kind]); n._id = uid(); list.push(n); openEntry[n._id] = true; changed(); renderForm();
        var f = $('[data-k^="' + kind + '.' + (list.length - 1) + '."]');
        if (f) { f.closest('.cr-entry, .cr-f').scrollIntoView({ behavior: 'smooth', block: 'center' }); f.focus({ preventScroll: true }); }
        break;
      case 'toggle': openEntry[list[i]._id] = !openEntry[list[i]._id]; renderForm(); break;
      case 'up': case 'down':
        var j = act === 'up' ? i - 1 : i + 1; if (j < 0 || j >= list.length) break;
        var tmp = list[i]; list[i] = list[j]; list[j] = tmp; S.order[kind] = 'manual'; changed(); renderForm(); break;
      case 'auto-order': S.order[kind] = 'auto'; changed(); renderForm(); break;
      case 'remove':
        var hasData = Object.keys(list[i]).some(function (k) { return k[0] !== '_' && k !== 'current' && list[i][k]; });
        if (hasData && !window.confirm('Remove this ' + NOUN[kind].toLowerCase() + ' entry?')) break;
        list.splice(i, 1); changed(); renderForm(); break;
      case 'reset':
        var key = b.dataset.sec, title = (SECTIONS.filter(function (s) { return s.key === key; })[0] || {}).title;
        if (!window.confirm('Clear everything in “' + title + '”?')) break;
        var fresh = empty();
        if (key === 'internships') { S.internships = []; S.volunteering = []; }
        else if (key === 'languages') { S.languages = []; S.additional = fresh.additional; }
        else S[key] = fresh[key];
        changed(); renderForm(); break;
      case 'sk-add': addSkills(b.dataset.cat); break;
      case 'sk-del': S.skills[b.dataset.cat].splice(i, 1); changed(); renderForm(); break;
      case 'sk-left': case 'sk-right':
        var arr = S.skills[b.dataset.cat], k2 = act === 'sk-left' ? i - 1 : i + 1;
        if (k2 >= 0 && k2 < arr.length) { var t2 = arr[i]; arr[i] = arr[k2]; arr[k2] = t2; changed(); renderForm(); }
        break;
      case 'sk-edit': editSkill(b.dataset.cat, i); break;
      case 'show-preview': document.getElementById('crPreview').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
      case 'edit':
        if (mode === 'pages') printPreview(document.getElementById('crPPBtn'));
        document.getElementById('crForm').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
      case 'zoom-in': zoom = Math.min(2, (zoom || fitZoom()) + 0.1); applyZoom(); break;
      case 'zoom-out': zoom = Math.max(0.3, (zoom || fitZoom()) - 0.1); applyZoom(); break;
      case 'zoom-fit': zoom = 0; applyZoom(); break;
      case 'page-prev': goPage(pageIdx - 1); break;
      case 'page-next': goPage(pageIdx + 1); break;
      case 'print-preview': printPreview(b); break;
      case 'print': printPdf(); break;
      case 'pdf': downloadPdf(b); break;
      case 'save': saveDraft(b); break;
      case 'new':
        if (!confirmDiscard()) break;
        draftId = null; draftSelect(); useState(empty());
        status(AUTH ? 'Started a new resume. Save Draft to keep it in your account.' : 'Started a new resume.', 'ok'); break;
      case 'delete':
        if (!draftId || !window.confirm('Delete this saved resume from your account? This cannot be undone.')) break;
        post(D.del.replace('/0/', '/' + draftId + '/'), {}).then(function (r) { return r.json(); }).then(function (d) {
          if (!d.ok) { status('The resume could not be deleted.', 'err'); return; }
          draftId = null; useState(empty()); status('Resume deleted.', 'ok'); return loadDrafts();
        });
        break;
    }
  });
  app.addEventListener('input', function (e) {
    var t = e.target, k = t.getAttribute('data-k');
    if (!k || t.tagName === 'SELECT') return;
    set(k, t.getAttribute('data-bool') ? t.checked : t.value);
    if (k === 'summary') updateCounter();
    changed();
  });
  app.addEventListener('change', function (e) {
    var t = e.target, k = t.getAttribute('data-k');
    if (t.id === 'crDraftSel') {
      var id = +t.value; if (!id || id === draftId) return;
      if (!confirmDiscard()) { draftSelect(); return; }
      loadDraft(id); return;
    }
    if (!k) return;
    if (t.tagName === 'SELECT') set(k, t.value);
    touched[k] = true;
    if (/\.current$/.test(k) || /\.(title|company|name|degree|qualification|institution|organization|role|issuer|type)$/.test(k) ||
        /_year$|_month$|\.year$|\.month$/.test(k)) {
      // Refresh the entry header / dependent fields (e.g. end date disabled while "current").
      if (/\.current$/.test(k)) renderForm();
      else { var head = t.closest('.cr-entry'), tEl = head && $('.t', head); if (tEl) { var p = k.split('.'); tEl.innerHTML = entryTitle(p[0], S[p[0]][+p[1]]); } }
    }
    changed(); applyStatus();
  });
  app.addEventListener('focusout', function (e) {
    var k = e.target.getAttribute && e.target.getAttribute('data-k');
    if (k) { touched[k] = true; applyStatus(); }
    if (e.target.dataset && e.target.dataset.skedit) commitSkill(e.target);
  });
  app.addEventListener('keydown', function (e) {
    var t = e.target;
    if (t.dataset && t.dataset.skadd && e.key === 'Enter') { e.preventDefault(); addSkills(t.dataset.skadd); }
    if (t.dataset && t.dataset.skedit) {
      if (e.key === 'Enter') { e.preventDefault(); t.blur(); }
      if (e.key === 'Escape') { e.preventDefault(); t.dataset.skedit && commitSkill(t, true); }
    }
  });
  window.addEventListener('beforeunload', function (e) {
    if (!dirty) return;
    e.preventDefault(); e.returnValue = '';
  });

  /* ───────────────────────── start ───────────────────────── */
  renderForm();
  if (AUTH) {
    loadDrafts().then(function (list) {
      if (list.length) { loadDraft(list[0].id); status('Opened your most recent resume. Choose another from “My resumes”.', 'ok'); }
      else schedulePreview(true);
    });
  } else {
    try {
      var saved = JSON.parse(localStorage.getItem(LOCAL_KEY) || 'null');
      if (saved && saved.personal) { useState(merge(saved)); status('Restored the draft saved on this device. <a href="' + esc(D.login) + '">Sign in</a> to save it to your account.', 'ok'); }
      else schedulePreview(true);
    } catch (e) { schedulePreview(true); }
  }
})();
