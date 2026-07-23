/* DOF-PREP — interface web hors-ligne. Utilise engine.js (logique) et store.js
 * (persistance locale). Aucune dependance, aucun reseau apres chargement.
 */
(function () {
  "use strict";
  var E = window.DOFEngine, S = window.DOFStore;
  var BANK = null, TAB = "dashboard";

  // --- Assistant IA (optionnel) : agent local detecte par sondage /health ---
  var AGENT = { checked: false, checking: false, ok: false, has_key: false, model: null };
  function agentUrl() { return (S.state.prefs.agent_url || "http://127.0.0.1:8799").replace(/\/+$/, ""); }
  function pingAgent(base) {
    return new Promise(function (resolve) {
      // Filet de securite : si fetch/AbortController est absent (vieux webview,
      // contexte restreint), on degrade proprement plutot que de faire planter
      // l'application ("agent non detecte" au lieu d'une erreur non geree).
      try {
        var ctrl = (typeof AbortController !== "undefined") ? new AbortController() : null;
        var to = setTimeout(function () { if (ctrl) ctrl.abort(); }, 1200);
        fetch(base + "/health", { signal: ctrl ? ctrl.signal : undefined })
          .then(function (r) { return r.json(); })
          .then(function (j) { clearTimeout(to); resolve({ ok: true, has_key: !!j.has_key, model: j.model || null }); })
          .catch(function () { clearTimeout(to); resolve({ ok: false, has_key: false, model: null }); });
      } catch (e) {
        resolve({ ok: false, has_key: false, model: null });
      }
    });
  }
  function refreshAgentStatus(cb) {
    AGENT.checking = true;
    pingAgent(agentUrl()).then(function (r) {
      AGENT.checked = true; AGENT.checking = false;
      AGENT.ok = r.ok; AGENT.has_key = r.has_key; AGENT.model = r.model;
      if (cb) cb();
    });
  }

  // --- helpers DOM ---
  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function pct(x) { return Math.round(x * 100) + " %"; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]; }); }
  function todayISO() { return new Date().toISOString().slice(0, 10); }

  function confLogs() {
    return S.state.confidence.map(function (r) { return { predicted: r.predicted, is_correct: r.is_correct, domain: r.domain }; });
  }
  function masteryMap() { return S.state.mastery; }

  // Enregistre les resultats d'une serie (maitrise, SM-2, confiance + Elo si actif)
  function recordResults(review, context, confidenceByQid) {
    var st = S.state, secondOrder = st.prefs.second_order;
    review.forEach(function (rv) {
      var qid = rv.question_id, code = BANK[qid].domain, isC = rv.is_correct;
      var m = st.mastery[code] || { score: 0, attempts: 0 };
      st.mastery[code] = E.updateMastery(m.score, m.attempts, isC);
      st.cards[qid] = E.sm2(st.cards[qid] || null, isC ? 5 : 2);
      st.attempts_total += 1;
      if (secondOrder && confidenceByQid && confidenceByQid[qid] != null) {
        var diff = (st.theta_item[qid] != null) ? st.theta_item[qid] : BANK[qid].theta_item;
        var up = E.secondOrderUpdate(st.theta_ability, diff, isC);
        st.theta_ability = up.ability; st.theta_item[qid] = up.diff;
        st.confidence.push({ predicted: confidenceByQid[qid] / 100, is_correct: isC ? 1 : 0, domain: code, context: context, ts: Date.now() });
      }
    });
    S.persist();
  }

  // --- navigation ---
  function tabs() {
    var list = [["dashboard", "Tableau de bord"], ["exam", "Examen blanc"], ["training", "Entrainement"], ["review", "Revision"]];
    if (S.state.prefs.second_order) list.push(["calibration", "Calibration"]);
    var nav = document.getElementById("tabs"); clear(nav);
    list.forEach(function (t) {
      var b = el("<button>" + t[1] + "</button>");
      if (t[0] === TAB) b.className = "active";
      b.onclick = function () { TAB = t[0]; render(); };
      nav.appendChild(b);
    });
  }
  function render() {
    if (TAB === "calibration" && !S.state.prefs.second_order) TAB = "dashboard";
    tabs();
    var v = document.getElementById("view"); clear(v);
    ({ dashboard: viewDashboard, exam: viewExam, training: viewTraining, review: viewReview, calibration: viewCalibration }[TAB] || viewDashboard)(v);
    try { window.scrollTo(0, 0); } catch (e) {}
  }

  // --- jauge SVG (demi-cercle) ---
  function gauge(readiness, target) {
    function pt(frac) { var a = (180 - 180 * frac) * Math.PI / 180; return [100 + 90 * Math.cos(a), 100 - 90 * Math.sin(a)]; }
    var e = pt(Math.max(0, Math.min(1, readiness)));
    var t = pt(Math.max(0, Math.min(1, target)));
    var ti = pt(Math.max(0, Math.min(1, target)) * 0.86); // base du repere cible
    var col = readiness >= target ? "#2f7d4f" : (readiness >= 0.65 ? "#0f766e" : "#b9770a");
    return "<svg viewBox='0 0 200 120' style='width:100%;max-width:320px;display:block;margin:0 auto'>" +
      "<path d='M10,100 A90,90 0 0,1 190,100' fill='none' stroke='#eef2f1' stroke-width='16' stroke-linecap='round'/>" +
      "<path d='M10,100 A90,90 0 0,1 " + e[0].toFixed(1) + "," + e[1].toFixed(1) + "' fill='none' stroke='" + col + "' stroke-width='16' stroke-linecap='round'/>" +
      "<line x1='" + ti[0].toFixed(1) + "' y1='" + ti[1].toFixed(1) + "' x2='" + t[0].toFixed(1) + "' y2='" + t[1].toFixed(1) + "' stroke='#1f2937' stroke-width='2'/>" +
      "<text x='100' y='86' text-anchor='middle' font-size='30' font-weight='800' fill='#1f2937'>" + Math.round(readiness * 100) + "%</text>" +
      "<text x='100' y='104' text-anchor='middle' font-size='10' fill='#6b7280'>preparation</text></svg>";
  }

  // --- Carte "Assistant IA" (optionnelle, degrade proprement si absente) ---
  function agentCard() {
    var st = S.state;
    var c = el("<div class='card'></div>");
    c.appendChild(el("<h2>Assistant IA (optionnel)</h2>"));

    var statusTxt, statusColor;
    if (AGENT.checking && !AGENT.checked) { statusTxt = "Verification..."; statusColor = "#6b7280"; }
    else if (AGENT.ok && AGENT.has_key) { statusTxt = "Agent detecte, cle API presente (" + esc(AGENT.model || "modele inconnu") + ")"; statusColor = "#2f7d4f"; }
    else if (AGENT.ok && !AGENT.has_key) { statusTxt = "Agent detecte, mais aucune cle API definie (ANTHROPIC_API_KEY)"; statusColor = "#b9770a"; }
    else { statusTxt = "Agent non detecte"; statusColor = "#6b7280"; }
    c.appendChild(el("<div class='note' style='color:" + statusColor + "'>" + statusTxt + "</div>"));

    var row = el("<div class='row' style='margin-top:6px'></div>");
    var input = el("<input type='text' style='flex:1;min-width:180px;padding:8px;border:1px solid var(--line);border-radius:8px'>");
    input.value = st.prefs.agent_url || "http://127.0.0.1:8799";
    input.onchange = function () { st.prefs.agent_url = input.value.trim() || "http://127.0.0.1:8799"; S.persist(); refreshAgentStatus(render); };
    row.appendChild(input);
    var check = el("<button class='btn ghost'>Verifier</button>");
    check.onclick = function () { refreshAgentStatus(render); };
    row.appendChild(check);
    c.appendChild(row);
    c.appendChild(el("<div class='note'>Lancez <code>python3 dof-prep-agent.py</code> en local (voir README_agent.md) pour activer ces fonctions. Rien n'est envoye sans action explicite de votre part ; sans agent, tout le reste continue de fonctionner hors-ligne.</div>"));

    if (!AGENT.ok) return c;

    // --- Analyse des lacunes ---
    var abtn = el("<button class='btn sec' style='margin-top:8px'>Analyser mes lacunes</button>");
    var aout = el("<div class='note'></div>");
    abtn.onclick = function () {
      abtn.disabled = true; aout.textContent = "Analyse en cours...";
      var secondOrder = st.prefs.second_order;
      var cal = secondOrder ? E.computeCalibration(confLogs()) : null;
      var rd = E.computeReadiness(masteryMap(), st.attempts_total, { secondOrder: secondOrder, calibration: cal });
      fetch(agentUrl() + "/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mastery: st.mastery, weak_domains: rd.weak_domains, readiness: rd.readiness, target: st.prefs.target_score }),
      }).then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
        .then(function (res) {
          abtn.disabled = false;
          aout.textContent = res.status === 200 ? res.body.analysis : ("Erreur : " + (res.body.error || res.status));
        }).catch(function () { abtn.disabled = false; aout.textContent = "Erreur reseau : agent injoignable."; });
    };
    c.appendChild(abtn); c.appendChild(aout);

    // --- Proposer des questions ---
    c.appendChild(el("<h2 style='margin-top:16px'>Proposer des questions</h2>"));
    var sel = el("<select style='padding:8px;border:1px solid var(--line);border-radius:8px'></select>");
    E.DOMAINS.forEach(function (d) { sel.appendChild(el("<option value='" + d.code + "'>" + d.code + " - " + esc(d.label) + "</option>")); });
    var cnt = el("<input type='number' min='1' max='10' value='5' style='width:64px;padding:8px;border:1px solid var(--line);border-radius:8px'>");
    var gbtn = el("<button class='btn sec'>Generer</button>");
    var grow = el("<div class='row' style='margin-top:6px'></div>");
    grow.appendChild(sel); grow.appendChild(cnt); grow.appendChild(gbtn);
    c.appendChild(grow);
    var gout = el("<div></div>");
    c.appendChild(gout);
    gbtn.onclick = function () {
      gbtn.disabled = true; clear(gout); gout.appendChild(el("<div class='note'>Generation en cours...</div>"));
      var domain = sel.value, count = Math.max(1, Math.min(10, parseInt(cnt.value, 10) || 5));
      var existing = BANK.filter(function (q) { return q.domain === domain; }).map(function (q) { return q.statement; }).slice(0, 40);
      fetch(agentUrl() + "/generate-questions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain, count: count, avoid_statements: existing }),
      }).then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
        .then(function (res) {
          gbtn.disabled = false; clear(gout);
          if (res.status !== 200) { gout.appendChild(el("<div class='note'>Erreur : " + esc(res.body.error || res.status) + "</div>")); return; }
          var qs = res.body.questions || [];
          gout.appendChild(el("<div class='note'>" + qs.length + " question(s) proposee(s) — a relire avant integration a la banque officielle.</div>"));
          qs.forEach(function (q) {
            var box = el("<div class='q'></div>");
            box.appendChild(el("<div class='small'>IA - a valider &middot; " + q.domain + " &middot; difficulte " + q.difficulty + "</div>"));
            box.appendChild(el("<div class='stmt'>" + esc(q.statement) + "</div>"));
            q.options.forEach(function (o) { box.appendChild(el("<div class='opt" + (o.correct ? " correct" : "") + "'><div>" + (o.correct ? "&#10003; " : "") + esc(o.text) + "</div></div>")); });
            if (q.explanation) box.appendChild(el("<div class='note'><b>Explication :</b> " + esc(q.explanation) + "</div>"));
            gout.appendChild(box);
          });
          var dl = el("<button class='btn ghost'>Telecharger ces questions (JSON)</button>");
          dl.onclick = function () {
            var blob = new Blob([JSON.stringify({ schema: "dof-prep-candidates", questions: qs }, null, 2)], { type: "application/json" });
            var a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "questions-ia-" + domain + "-" + Date.now() + ".json";
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
          };
          gout.appendChild(dl);
        }).catch(function () { gbtn.disabled = false; clear(gout); gout.appendChild(el("<div class='note'>Erreur reseau : agent injoignable.</div>")); });
    };
    return c;
  }

  // --- VUE : Tableau de bord ---
  function viewDashboard(v) {
    var st = S.state, secondOrder = st.prefs.second_order, target = st.prefs.target_score;
    var cal = secondOrder ? E.computeCalibration(confLogs()) : null;
    var rd = E.computeReadiness(masteryMap(), st.attempts_total, { secondOrder: secondOrder, calibration: cal });
    var recs = E.buildRecommendations(rd, target);

    var c1 = el("<div class='card'></div>");
    c1.appendChild(el("<h2>Etat de preparation</h2>"));
    c1.appendChild(el(gauge(rd.readiness, target)));
    var k = el("<div class='kpi center' style='justify-content:center;margin-top:6px'></div>");
    k.appendChild(el("<div><div class='v'>" + pct(rd.readiness_raw) + "</div><div class='l'>preparation brute</div></div>"));
    if (secondOrder) k.appendChild(el("<div><div class='v'>x" + rd.calibration_factor.toFixed(2) + "</div><div class='l'>facteur calibration</div></div>"));
    k.appendChild(el("<div><div class='v'>" + pct(rd.confidence) + "</div><div class='l'>confiance des donnees</div></div>"));
    k.appendChild(el("<div><div class='v'>" + st.attempts_total + "</div><div class='l'>reponses cumulees</div></div>"));
    c1.appendChild(k);
    c1.appendChild(el("<div class='note center'>Seuil officiel 65 %. Le repere noir indique votre cible.</div>"));
    v.appendChild(c1);

    // Reglages
    var c2 = el("<div class='card'></div>");
    c2.appendChild(el("<h2>Reglages</h2>"));
    var slabel = el("<div class='note'>Score cible : <b id='tgtval'>" + Math.round(target * 100) + " %</b> (65 a 90)</div>");
    c2.appendChild(slabel);
    var slider = el("<input type='range' min='65' max='90' step='1' value='" + Math.round(target * 100) + "'>");
    slider.oninput = function () { document.getElementById("tgtval").textContent = slider.value + " %"; };
    slider.onchange = function () { st.prefs.target_score = parseInt(slider.value, 10) / 100; S.persist(); render(); };
    c2.appendChild(slider);
    var sw = el("<label class='switch' style='margin-top:10px'><input type='checkbox' " + (secondOrder ? "checked" : "") + "> <span>Activer la couche de second ordre (calibration metacognitive)</span></label>");
    sw.querySelector("input").onchange = function (ev) { st.prefs.second_order = ev.target.checked; S.persist(); render(); };
    c2.appendChild(sw);
    c2.appendChild(el("<div class='note'>Quand elle est active, une question de confiance accompagne chaque reponse, l'onglet Calibration apparait, et la preparation est ponderee par votre calibration (jamais sous le plancher).</div>"));
    v.appendChild(c2);

    // Maitrise par domaine
    var c3 = el("<div class='card'></div>");
    c3.appendChild(el("<h2>Maitrise par domaine</h2>"));
    rd.per_domain.forEach(function (d) {
      var row = el("<div style='margin:8px 0'></div>");
      row.appendChild(el("<div class='spread'><div><b>" + d.code + "</b> <span class='small'>" + esc(d.label) + "</span></div><div class='small'>" + pct(d.mastery) + " &middot; " + d.attempts + " rep.</div></div>"));
      var bar = el("<div class='bar' style='margin-top:4px'></div>");
      var span = el("<span></span>"); span.style.width = Math.round(d.mastery * 100) + "%";
      if (d.mastery < 0.65) span.style.background = "#b9770a";
      bar.appendChild(span); row.appendChild(bar);
      c3.appendChild(row);
    });
    v.appendChild(c3);

    // Recommandations
    var c4 = el("<div class='card'></div>");
    c4.appendChild(el("<h2>Recommandations</h2>"));
    var ul = el("<ul style='margin:0;padding-left:18px'></ul>");
    recs.forEach(function (r) { ul.appendChild(el("<li style='margin:4px 0'>" + esc(r) + "</li>")); });
    c4.appendChild(ul);
    v.appendChild(c4);

    v.appendChild(agentCard());

    var c5 = el("<div class='card'></div>");
    c5.appendChild(el("<div class='spread'><div class='small'>Donnees stockees uniquement sur cet appareil.</div></div>"));
    var rb = el("<button class='btn ghost'>Reinitialiser ma progression</button>");
    rb.onclick = function () { if (confirm("Effacer toute votre progression locale ?")) { S.reset(); TAB = "dashboard"; render(); } };
    c5.appendChild(rb);
    v.appendChild(c5);
  }

  // --- VUE : Examen blanc ---
  var examState = null;
  function viewExam(v) {
    if (examState) return renderExamRunning(v);
    var c = el("<div class='card'></div>");
    c.appendChild(el("<h2>Examens blancs</h2>"));
    c.appendChild(el("<div class='note'>40 questions, seuil 65 %, sans penalite. Les 4 examens d'un meme niveau ne se recouvrent pas.</div>"));
    ["moyen", "difficile", "tres_difficile"].forEach(function (lv) {
      c.appendChild(el("<div style='margin-top:10px;font-weight:600'>" + E.LEVEL_LABEL[lv] + "</div>"));
      var g = el("<div class='grid'></div>");
      E.EXAM_PRESETS.filter(function (p) { return p.level === lv; }).forEach(function (p) {
        var b = el("<button class='btn sec'>Examen " + p.id + "</button>");
        b.onclick = function () { startExam(E.presetExam(BANK, p.id).ids, "Examen blanc " + p.id); };
        g.appendChild(b);
      });
      c.appendChild(g);
    });
    v.appendChild(c);

    var c2 = el("<div class='card'></div>");
    c2.appendChild(el("<h2>Examen libre</h2>"));
    c2.appendChild(el("<div class='note'>Genere un examen aleatoire au niveau choisi (ponderation exacte).</div>"));
    var g2 = el("<div class='grid'></div>");
    ["moyen", "difficile", "tres_difficile"].forEach(function (lv) {
      var b = el("<button class='btn'>" + E.LEVEL_LABEL[lv] + "</button>");
      b.onclick = function () { startExam(E.generateExam(BANK, { level: lv, seed: Math.floor(Math.random() * 1e9) }), "Examen libre (" + E.LEVEL_LABEL[lv] + ")"); };
      g2.appendChild(b);
    });
    c2.appendChild(g2);
    v.appendChild(c2);
  }
  function startExam(ids, label) { examState = { ids: ids, label: label, answers: {}, conf: {}, submitted: null }; render(); }

  function questionCard(qid, idx, opts) {
    opts = opts || {};
    var q = BANK[qid];
    var card = el("<div class='q'></div>");
    card.appendChild(el("<div class='small'>Question " + (idx + 1) + " &middot; " + q.domain + " &middot; difficulte " + q.difficulty + " &middot; " + (q.type === "multiple" ? "choix multiple" : (q.type === "truefalse" ? "vrai/faux" : "choix unique")) + "</div>"));
    card.appendChild(el("<div class='stmt'>" + esc(q.statement) + "</div>"));
    var multiple = q.type === "multiple";
    q.options.forEach(function (o) {
      var lab = el("<label class='opt'></label>");
      var inp = el("<input type='" + (multiple ? "checkbox" : "radio") + "' name='q" + qid + "' value='" + o.id + "'>");
      lab.appendChild(inp);
      lab.appendChild(el("<div>" + esc(o.text) + "</div>"));
      card.appendChild(lab);
    });
    return card;
  }
  function readSelection(qid) {
    var inputs = document.querySelectorAll("input[name='q" + qid + "']");
    var sel = [];
    inputs.forEach(function (i) { if (i.checked) sel.push(i.value); });
    return sel;
  }
  function confidenceRow(qid, store) {
    var wrap = el("<div class='conf'></div>");
    wrap.appendChild(el("<span class='small' style='align-self:center'>Confiance :</span>"));
    E.CONFIDENCE_CHOICES.forEach(function (p) {
      var b = el("<button>" + p + " %</button>");
      if (store[qid] === p) b.className = "sel";
      b.onclick = function () { store[qid] = p; wrap.querySelectorAll("button").forEach(function (x) { x.className = ""; }); b.className = "sel"; };
      wrap.appendChild(b);
    });
    return wrap;
  }

  function renderExamRunning(v) {
    var st = S.state, secondOrder = st.prefs.second_order;
    if (examState.submitted) return renderExamResult(v);
    var head = el("<div class='card'></div>");
    head.appendChild(el("<div class='spread'><h2 style='margin:0'>" + esc(examState.label) + "</h2><span class='pill'>" + examState.ids.length + " questions</span></div>"));
    head.appendChild(el("<div class='note'>Repondez a toutes les questions puis validez. Seuil de reussite : 65 %.</div>"));
    v.appendChild(head);

    examState.ids.forEach(function (qid, i) {
      var card = questionCard(qid, i);
      if (secondOrder) card.appendChild(confidenceRow(qid, examState.conf));
      v.appendChild(card);
    });

    var foot = el("<div class='card'></div>");
    var submit = el("<button class='btn'>Terminer et corriger</button>");
    submit.onclick = function () {
      var answers = examState.ids.map(function (qid) { return { question_id: qid, selected_option_ids: readSelection(qid) }; });
      var res = E.gradeAnswers(BANK, answers);
      recordResults(res.review, "exam", secondOrder ? examState.conf : null);
      st.history.push({ ts: Date.now(), kind: "exam", score: res.score, correct: res.correct, total: res.total, label: examState.label });
      S.persist();
      examState.submitted = res; render();
    };
    foot.appendChild(submit);
    var quit = el("<button class='btn ghost' style='margin-left:8px'>Abandonner</button>");
    quit.onclick = function () { examState = null; render(); };
    foot.appendChild(quit);
    v.appendChild(foot);
  }

  function renderExamResult(v) {
    var res = examState.submitted, passed = res.score >= E.PASS_THRESHOLD;
    var c = el("<div class='card center'></div>");
    c.appendChild(el("<h2>Resultat — " + esc(examState.label) + "</h2>"));
    c.appendChild(el("<div class='result-score'>" + pct(res.score) + "</div>"));
    c.appendChild(el("<div class='" + (passed ? "tag-ok" : "tag-ko") + "'>" + (passed ? "Reussite" : "Echec") + " &middot; " + res.correct + "/" + res.total + " &middot; seuil 65 %</div>"));
    v.appendChild(c);

    var cd = el("<div class='card'></div>");
    cd.appendChild(el("<h2>Par domaine</h2>"));
    var tb = el("<table><thead><tr><th>Domaine</th><th>Juste</th><th>Taux</th></tr></thead><tbody></tbody></table>");
    var body = tb.querySelector("tbody");
    res.by_domain.forEach(function (d) { body.appendChild(el("<tr><td>" + d.domain + "</td><td>" + d.correct + "/" + d.total + "</td><td>" + pct(d.rate) + "</td></tr>")); });
    cd.appendChild(tb); v.appendChild(cd);

    var cr = el("<div class='card'></div>");
    cr.appendChild(el("<h2>Correction detaillee</h2>"));
    res.review.forEach(function (rv, i) {
      var q = BANK[rv.question_id];
      var box = el("<div class='q'></div>");
      box.appendChild(el("<div class='small'>Q" + (i + 1) + " &middot; " + q.domain + " &middot; <span class='" + (rv.is_correct ? "tag-ok" : "tag-ko") + "'>" + (rv.is_correct ? "juste" : "faux") + "</span></div>"));
      box.appendChild(el("<div class='stmt'>" + esc(q.statement) + "</div>"));
      q.options.forEach(function (o) {
        var good = rv.correct_option_ids.indexOf(o.id) !== -1;
        var chosen = rv.selected_option_ids.indexOf(o.id) !== -1;
        var cls = good ? "opt correct" : (chosen ? "opt wrong" : "opt");
        box.appendChild(el("<div class='" + cls + "'><div>" + (good ? "&#10003; " : (chosen ? "&#10007; " : "")) + esc(o.text) + "</div></div>"));
      });
      if (q.explanation) box.appendChild(el("<div class='note'><b>Explication :</b> " + esc(q.explanation) + "</div>"));
      cr.appendChild(box);
    });
    v.appendChild(cr);

    var foot = el("<div class='card'></div>");
    var again = el("<button class='btn'>Retour aux examens</button>");
    again.onclick = function () { examState = null; render(); };
    foot.appendChild(again);
    v.appendChild(foot);
  }

  // --- VUE : Entrainement ---
  var trainState = null;
  function viewTraining(v) {
    if (!trainState) {
      var c = el("<div class='card'></div>");
      c.appendChild(el("<h2>Entrainement par domaine</h2>"));
      c.appendChild(el("<div class='note'>Questions tirees du domaine choisi, avec correction immediate.</div>"));
      var g = el("<div class='grid'></div>");
      E.DOMAINS.forEach(function (d) {
        var b = el("<button class='btn sec' style='text-align:left'>" + d.code + "<div class='small'>" + esc(d.label) + "</div></button>");
        b.onclick = function () { trainState = { domain: d.code, pool: poolFor(d.code), qid: null, revealed: false, conf: {} }; nextTrain(); render(); };
        g.appendChild(b);
      });
      c.appendChild(g);
      v.appendChild(c);
      return;
    }
    renderTrain(v);
  }
  function poolFor(code) { var ids = BANK.filter(function (q) { return q.domain === code; }).map(function (q) { return q.id; }); return E.mulberry32 ? shuffleCopy(ids) : ids; }
  function shuffleCopy(a) { a = a.slice(); var rng = E.mulberry32(Math.floor(Math.random() * 1e9)); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(rng() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function nextTrain() { if (!trainState.pool.length) trainState.pool = poolFor(trainState.domain); trainState.qid = trainState.pool.shift(); trainState.revealed = false; trainState.conf = {}; }

  function renderTrain(v) {
    var st = S.state, secondOrder = st.prefs.second_order, qid = trainState.qid;
    var head = el("<div class='card'></div>");
    head.appendChild(el("<div class='spread'><h2 style='margin:0'>Entrainement — " + trainState.domain + "</h2><button class='btn ghost' id='backtrain'>Changer de domaine</button></div>"));
    v.appendChild(head);
    document.getElementById("backtrain") && (document.getElementById("backtrain").onclick = function () { trainState = null; render(); });

    var card = questionCard(qid, 0);
    if (secondOrder && !trainState.revealed) card.appendChild(confidenceRow(qid, trainState.conf));
    var holder = el("<div class='card'></div>"); holder.appendChild(card);

    if (!trainState.revealed) {
      var check = el("<button class='btn'>Valider</button>");
      check.onclick = function () {
        var sel = readSelection(qid);
        var res = E.gradeAnswers(BANK, [{ question_id: qid, selected_option_ids: sel }]);
        recordResults(res.review, "training", secondOrder ? trainState.conf : null);
        trainState.revealed = res.review[0]; render();
      };
      holder.appendChild(check);
    } else {
      var rv = trainState.revealed, q = BANK[qid];
      var fb = el("<div class='note'><span class='" + (rv.is_correct ? "tag-ok" : "tag-ko") + "'>" + (rv.is_correct ? "Juste" : "Faux") + "</span></div>");
      holder.appendChild(fb);
      // marque les options
      holder.querySelectorAll(".opt").forEach(function (node, i) {
        var o = q.options[i];
        if (rv.correct_option_ids.indexOf(o.id) !== -1) node.className = "opt correct";
        else if (rv.selected_option_ids.indexOf(o.id) !== -1) node.className = "opt wrong";
        node.querySelector("input").disabled = true;
      });
      if (q.explanation) holder.appendChild(el("<div class='note'><b>Explication :</b> " + esc(q.explanation) + "</div>"));
      var next = el("<button class='btn'>Question suivante</button>");
      next.onclick = function () { nextTrain(); render(); };
      holder.appendChild(next);
    }
    v.appendChild(holder);
  }

  // --- VUE : Revision (SM-2) ---
  var reviewState = null;
  function viewReview(v) {
    var st = S.state, today = todayISO();
    if (!reviewState) {
      var due = Object.keys(st.cards).filter(function (qid) { return st.cards[qid].due_date <= today && BANK[qid]; });
      if (!due.length) {
        var c = el("<div class='card center'></div>");
        c.appendChild(el("<h2>Revision espacee</h2>"));
        c.appendChild(el("<div class='note'>Aucune carte a reviser aujourd'hui. Les cartes apparaissent apres vos reponses (algorithme SM-2) et reviennent a echeance.</div>"));
        v.appendChild(c); return;
      }
      reviewState = { due: due, i: 0, conf: {}, revealed: false };
    }
    renderReview(v);
  }
  function renderReview(v) {
    var st = S.state, secondOrder = st.prefs.second_order;
    if (reviewState.i >= reviewState.due.length) {
      var done = el("<div class='card center'></div>");
      done.appendChild(el("<h2>Revision terminee</h2>"));
      done.appendChild(el("<div class='note'>" + reviewState.due.length + " carte(s) revisee(s). A demain pour les prochaines echeances.</div>"));
      var b = el("<button class='btn'>Terminer</button>"); b.onclick = function () { reviewState = null; render(); }; done.appendChild(b);
      v.appendChild(done); reviewState = null; return;
    }
    var qid = reviewState.due[reviewState.i];
    var head = el("<div class='card'></div>");
    head.appendChild(el("<div class='spread'><h2 style='margin:0'>Revision</h2><span class='pill'>" + (reviewState.i + 1) + " / " + reviewState.due.length + "</span></div>"));
    v.appendChild(head);
    var card = questionCard(qid, reviewState.i);
    if (secondOrder && !reviewState.revealed) card.appendChild(confidenceRow(qid, reviewState.conf));
    var holder = el("<div class='card'></div>"); holder.appendChild(card);
    if (!reviewState.revealed) {
      var check = el("<button class='btn'>Valider</button>");
      check.onclick = function () {
        var sel = readSelection(qid);
        var res = E.gradeAnswers(BANK, [{ question_id: qid, selected_option_ids: sel }]);
        recordResults(res.review, "review", secondOrder ? reviewState.conf : null);
        reviewState.revealed = res.review[0]; render();
      };
      holder.appendChild(check);
    } else {
      var rv = reviewState.revealed, q = BANK[qid];
      holder.appendChild(el("<div class='note'><span class='" + (rv.is_correct ? "tag-ok" : "tag-ko") + "'>" + (rv.is_correct ? "Juste" : "Faux") + "</span></div>"));
      holder.querySelectorAll(".opt").forEach(function (node, i) {
        var o = q.options[i];
        if (rv.correct_option_ids.indexOf(o.id) !== -1) node.className = "opt correct";
        else if (rv.selected_option_ids.indexOf(o.id) !== -1) node.className = "opt wrong";
        node.querySelector("input").disabled = true;
      });
      if (q.explanation) holder.appendChild(el("<div class='note'><b>Explication :</b> " + esc(q.explanation) + "</div>"));
      var next = el("<button class='btn'>Suivante</button>");
      next.onclick = function () { reviewState.i += 1; reviewState.revealed = false; reviewState.conf = {}; render(); };
      holder.appendChild(next);
    }
    v.appendChild(holder);
  }

  // --- VUE : Calibration ---
  function viewCalibration(v) {
    var cal = E.computeCalibration(confLogs());
    if (!cal.available) {
      var c = el("<div class='card'></div>");
      c.appendChild(el("<h2>Calibration metacognitive</h2>"));
      c.appendChild(el("<div class='note'>Repondez avec une estimation de confiance (examen ou entrainement) pour alimenter cette analyse.</div>"));
      v.appendChild(c); return;
    }
    var c1 = el("<div class='card'></div>");
    c1.appendChild(el("<h2>Calibration metacognitive</h2>"));
    var biais = cal.gap > 0.05 ? "tendance a la SUR-confiance" : (cal.gap < -0.05 ? "tendance a la SOUS-confiance" : "bonne calibration globale");
    c1.appendChild(el("<div class='note'>" + cal.n + " predictions &middot; " + biais + "</div>"));
    var k = el("<div class='kpi'></div>");
    k.appendChild(el("<div><div class='v'>" + cal.brier.toFixed(3) + "</div><div class='l'>score de Brier (bas = mieux)</div></div>"));
    k.appendChild(el("<div><div class='v'>" + cal.ece.toFixed(3) + "</div><div class='l'>erreur de calibration (ECE)</div></div>"));
    k.appendChild(el("<div><div class='v'>" + pct(cal.mean_predicted) + "</div><div class='l'>confiance moyenne</div></div>"));
    k.appendChild(el("<div><div class='v'>" + pct(cal.mean_actual) + "</div><div class='l'>reussite reelle</div></div>"));
    k.appendChild(el("<div><div class='v'>x" + cal.calibration_factor.toFixed(2) + "</div><div class='l'>facteur (applique : " + (cal.applies ? "oui" : "non, <" + cal.min_records + ")") + "</div></div>"));
    c1.appendChild(k);
    v.appendChild(c1);

    // Courbe de fiabilite
    var c2 = el("<div class='card'></div>");
    c2.appendChild(el("<h2>Courbe de fiabilite</h2>"));
    var tb = el("<table><thead><tr><th>Tranche</th><th>n</th><th>Confiance</th><th>Reussite</th><th>Ecart</th></tr></thead><tbody></tbody></table>");
    var body = tb.querySelector("tbody");
    cal.bins.forEach(function (b) {
      if (b.n === 0) { body.appendChild(el("<tr><td>" + b.label + "</td><td>0</td><td>-</td><td>-</td><td>-</td></tr>")); return; }
      var gap = (b.predicted - b.actual);
      body.appendChild(el("<tr><td>" + b.label + "</td><td>" + b.n + "</td><td>" + pct(b.predicted) + "</td><td>" + pct(b.actual) + "</td><td>" + (gap >= 0 ? "+" : "") + Math.round(gap * 100) + " pts</td></tr>"));
    });
    c2.appendChild(tb); v.appendChild(c2);

    // Tendance du Brier
    if (cal.trend && cal.trend.available) {
      var c3 = el("<div class='card'></div>");
      c3.appendChild(el("<h2>Tendance du score de Brier</h2>"));
      var dir = cal.trend.direction, txt, col;
      if (dir === "amelioration") { txt = "Calibration en amelioration"; col = "#2f7d4f"; }
      else if (dir === "degradation") { txt = "Calibration en recul"; col = "#b1442f"; }
      else { txt = "Calibration stable"; col = "#5c6b73"; }
      c3.appendChild(el("<div style='font-weight:700;color:" + col + "'>" + txt + "</div>"));
      c3.appendChild(el("<div class='note'>1re moitie : " + cal.trend.first_half_brier.toFixed(3) + " &middot; 2de moitie : " + cal.trend.second_half_brier.toFixed(3) + " (plus bas = mieux)</div>"));
      var bars = el("<div class='bars'></div>");
      cal.trend.buckets.forEach(function (b) {
        var quality = Math.max(0, Math.min(1, 1 - b.brier));
        var col2 = el("<div class='b'></div>");
        col2.appendChild(el("<div class='small'>" + b.brier.toFixed(2) + "</div>"));
        var bv = el("<div class='bv'></div>"); bv.style.height = Math.round(8 + quality * 100) + "px"; bv.title = "tranche " + b.i + " (" + b.n + ")";
        col2.appendChild(bv);
        col2.appendChild(el("<div class='small'>" + b.i + "</div>"));
        bars.appendChild(col2);
      });
      c3.appendChild(bars);
      c3.appendChild(el("<div class='small'>Chaque barre = une tranche chronologique ; hauteur proportionnelle a la qualite (1 - Brier).</div>"));
      v.appendChild(c3);
    }

    // Par domaine
    if (cal.per_domain.length) {
      var c4 = el("<div class='card'></div>");
      c4.appendChild(el("<h2>Par domaine</h2>"));
      var t2 = el("<table><thead><tr><th>Domaine</th><th>n</th><th>Confiance</th><th>Reussite</th><th>Ecart</th></tr></thead><tbody></tbody></table>");
      var b2 = t2.querySelector("tbody");
      cal.per_domain.forEach(function (d) { b2.appendChild(el("<tr><td>" + d.domain + "</td><td>" + d.n + "</td><td>" + pct(d.predicted) + "</td><td>" + pct(d.actual) + "</td><td>" + (d.gap >= 0 ? "+" : "") + Math.round(d.gap * 100) + " pts</td></tr>")); });
      c4.appendChild(t2); v.appendChild(c4);
    }
  }

  // --- amorcage ---
  function boot(data) {
    BANK = E.loadBank(data);
    render();                       // rendu immediat, hors-ligne, sans attendre l'agent
    refreshAgentStatus(function () { if (TAB === "dashboard") render(); });
  }
  if (window.__DOF_BANK__) {
    boot(window.__DOF_BANK__);              // mode fichier autonome (banque inlinee)
  } else {
    fetch("questions.json").then(function (r) { return r.json(); }).then(boot).catch(function (e) {
      document.getElementById("view").appendChild(el("<div class='card'><h2>Erreur</h2><div class='note'>Impossible de charger la banque de questions (questions.json). Servez le dossier via un petit serveur, ou utilisez la version autonome.</div></div>"));
    });
  }
  window.addEventListener("online", function () {}); // l'app fonctionne hors-ligne
})();
