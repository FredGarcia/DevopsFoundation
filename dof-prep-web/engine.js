/* DOF-PREP — moteur applicatif porte depuis la version Python (stdlib).
 * Logique pure, sans dependance : meme banque questions.json, memes garanties
 * (ponderation exacte, recouvrement nul "par donne", SM-2, calibration/Brier,
 * Elo de second ordre, preparation). Utilisable dans le navigateur ET sous Node
 * (pour la suite de tests de parite). Aucun reseau, aucune dependance externe.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DOFEngine = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // --- Constantes (identiques a la version Python) ---
  var CERT_CODE = "DOFD_V3_4";
  var QUESTION_COUNT = 40;
  var PASS_THRESHOLD = 0.65;
  var DURATION_MIN = 60;
  var TARGET_MIN = 0.65, TARGET_MAX = 0.90, TARGET_DEFAULT = 0.90;
  var DATA_CONFIDENCE_THRESHOLD = 80;
  var DOMAIN_FLOOR = 0.65;
  var DIFF_LOGIT_SCALE = 0.85;
  var ELO_K = 0.08;
  var CALIB_MIN_RECORDS = 20;
  var CALIB_FLOOR = 0.60;
  var CONFIDENCE_CHOICES = [25, 50, 75, 95];

  var DOMAINS = [
    { code: "DOFD-1", label: "Explorer le DevOps", weight: 5 / 40 },
    { code: "DOFD-2", label: "Principes fondamentaux du DevOps (les Trois Voies)", weight: 4 / 40 },
    { code: "DOFD-3", label: "Pratiques cles du DevOps", weight: 7 / 40 },
    { code: "DOFD-4", label: "Cadres metier et techniques", weight: 7 / 40 },
    { code: "DOFD-5", label: "Valeurs DevOps : culture, comportements et modeles operationnels", weight: 6 / 40 },
    { code: "DOFD-6", label: "Valeurs DevOps : automatisation et architecture des chaines d'outils", weight: 5 / 40 },
    { code: "DOFD-7", label: "Valeurs DevOps : mesure, metriques et reporting", weight: 2 / 40 },
    { code: "DOFD-8", label: "Valeurs DevOps : partage, accompagnement et evolution", weight: 4 / 40 },
  ];
  var DOMAIN_CODES = DOMAINS.map(function (d) { return d.code; });
  var DOMAIN_LABEL = {};
  DOMAINS.forEach(function (d) { DOMAIN_LABEL[d.code] = d.label; });

  var LEVEL_BANDS = { moyen: [2, 3], difficile: [3, 4], tres_difficile: [4, 5] };
  var LEVEL_LABEL = { moyen: "Moyen", difficile: "Difficile", tres_difficile: "Tres difficile" };
  var EXAM_PRESETS = [];
  ["moyen", "difficile", "tres_difficile"].forEach(function (lv, gi) {
    for (var k = 1; k <= 4; k++) EXAM_PRESETS.push({ id: gi * 4 + k, level: lv });
  });
  var PRESET_BAND_SEED = { moyen: 70001, difficile: 70002, tres_difficile: 70003 };

  // --- Utilitaires ---
  function round(x, n) { var f = Math.pow(10, n || 0); return Math.round(x * f) / f; }
  function r4(x) { return round(x, 4); }

  // PRNG deterministe (mulberry32) : rend les examens reproductibles cote web.
  // (N.B. : algorithme propre au build web ; il garantit les memes INVARIANTS
  //  que la version Python — ponderation exacte, recouvrement nul, reproductibilite
  //  — sans pretendre tirer les memes identifiants que le Mersenne Twister de CPython.)
  function mulberry32(seed) {
    var a = (seed >>> 0) || 1;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function shuffle(arr, rng) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }
  function bandHas(level, diff) { var b = LEVEL_BANDS[level]; return b && b.indexOf(diff) !== -1; }

  // --- Chargement / normalisation de la banque ---
  // Chaque question recoit un id stable = son index dans la banque ; chaque option
  // un id `${qi}:${oi}`. theta_item latent initialise a (difficulty-3)*0.85.
  function loadBank(data) {
    var qs = (data && data.questions) || [];
    return qs.map(function (q, qi) {
      return {
        id: qi,
        domain: q.domain,
        k_level: q.k_level,
        difficulty: q.difficulty,
        type: q.type || "single",
        statement: q.statement,
        explanation: q.explanation || "",
        theta_item: (q.difficulty - 3) * DIFF_LOGIT_SCALE,
        options: (q.options || []).map(function (o, oi) {
          return { id: qi + ":" + oi, text: o.text, correct: !!o.correct };
        }),
      };
    });
  }
  function byDomain(bank) {
    var m = {}; DOMAIN_CODES.forEach(function (c) { m[c] = []; });
    bank.forEach(function (q) { if (m[q.domain]) m[q.domain].push(q); });
    return m;
  }

  // --- Quotas (methode du plus grand reste, portage fidele) ---
  function computeQuotas(count) {
    var raw = DOMAINS.map(function (d, i) { return { id: i, code: d.code, val: d.weight * count }; });
    var quotas = {}; raw.forEach(function (r) { quotas[r.code] = Math.floor(r.val); });
    var assigned = raw.reduce(function (s, r) { return s + Math.floor(r.val); }, 0);
    var remainder = count - assigned;
    var fracs = raw.map(function (r) { return { frac: r.val - Math.floor(r.val), id: r.id, code: r.code }; })
      .sort(function (a, b) { return (b.frac - a.frac) || (b.id - a.id); });
    var idx = 0;
    while (remainder > 0 && fracs.length) {
      var f = fracs[idx % fracs.length];
      quotas[f.code] += 1; remainder -= 1; idx += 1;
    }
    return quotas;
  }

  // --- Generation d'un examen (ponderation stricte + biais de bande + repli) ---
  function generateExam(bank, opts) {
    opts = opts || {};
    var level = opts.level || null;
    var rng = mulberry32(opts.seed != null ? opts.seed : Math.floor(Math.random() * 1e9));
    var count = QUESTION_COUNT;
    var quotas = computeQuotas(count);
    var groups = byDomain(bank);
    var chosen = [], used = {};
    DOMAINS.forEach(function (d) {
      var rows = groups[d.code] || [];
      var ordered;
      if (level) {
        var inB = rows.filter(function (q) { return bandHas(level, q.difficulty); }).map(function (q) { return q.id; });
        var outB = rows.filter(function (q) { return !bandHas(level, q.difficulty); }).map(function (q) { return q.id; });
        shuffle(inB, rng); shuffle(outB, rng);
        ordered = inB.concat(outB);
      } else {
        ordered = rows.map(function (q) { return q.id; });
        shuffle(ordered, rng);
      }
      var take = Math.min(quotas[d.code], ordered.length);
      for (var i = 0; i < take; i++) { chosen.push(ordered[i]); used[ordered[i]] = true; }
    });
    if (chosen.length < count) {
      var pool = bank.map(function (q) { return q.id; }).filter(function (id) { return !used[id]; });
      shuffle(pool, rng);
      for (var j = 0; j < pool.length && chosen.length < count; j++) { chosen.push(pool[j]); used[pool[j]] = true; }
    }
    shuffle(chosen, rng);
    return chosen;
  }

  // --- 12 examens "par donne" : recouvrement nul par construction ---
  function buildBandExams(bank, level, nExams) {
    nExams = nExams || 4;
    var count = QUESTION_COUNT;
    var quotas = computeQuotas(count);
    var base = PRESET_BAND_SEED[level];
    var groups = byDomain(bank);
    var exams = []; for (var e = 0; e < nExams; e++) exams.push([]);
    DOMAINS.forEach(function (d, di) {
      var rows = groups[d.code] || [];
      var inB = rows.filter(function (q) { return bandHas(level, q.difficulty); }).map(function (q) { return q.id; });
      var outB = rows.filter(function (q) { return !bandHas(level, q.difficulty); }).map(function (q) { return q.id; });
      var rng = mulberry32(base * 1000 + di);
      shuffle(inB, rng); shuffle(outB, rng);
      var seq = inB.concat(outB);
      var q = quotas[d.code], need = q * nExams;
      while (seq.length < need) { var extra = inB.concat(outB); shuffle(extra, rng); seq = seq.concat(extra); }
      for (var k = 0; k < need; k++) exams[k % nExams].push(seq[k]);
    });
    for (var i = 0; i < nExams; i++) shuffle(exams[i], mulberry32(base + 7 * i));
    return exams;
  }

  function presetInfo(p) {
    return { id: p.id, level: p.level, level_label: LEVEL_LABEL[p.level], name: "Examen blanc " + p.id, seed: 4100 + p.id };
  }
  function presetExam(bank, presetId) {
    var p = EXAM_PRESETS.filter(function (x) { return x.id === presetId; })[0];
    if (!p) return null;
    // Indice de l'examen dans son niveau (0..3) -> on prend la donne correspondante.
    var withinLevel = EXAM_PRESETS.filter(function (x) { return x.level === p.level; }).map(function (x) { return x.id; }).sort(function (a, b) { return a - b; }).indexOf(p.id);
    var exams = buildBandExams(bank, p.level, 4);
    return { info: presetInfo(p), ids: exams[withinLevel] };
  }

  // --- Correction ---
  function setEqual(a, b) {
    if (a.length !== b.length) return false;
    var s = {}; a.forEach(function (x) { s[x] = true; });
    for (var i = 0; i < b.length; i++) if (!s[b[i]]) return false;
    return true;
  }
  function gradeAnswers(bank, answers) {
    var byId = {}; bank.forEach(function (q) { byId[q.id] = q; });
    var review = [], dom = {}, correctCount = 0;
    answers.forEach(function (ans) {
      var q = byId[ans.question_id]; if (!q) return;
      var selected = (ans.selected_option_ids || []).slice();
      var correctIds = q.options.filter(function (o) { return o.correct; }).map(function (o) { return o.id; });
      var isCorrect = selected.length > 0 && setEqual(selected, correctIds);
      if (isCorrect) correctCount++;
      var agg = dom[q.domain] || (dom[q.domain] = { correct: 0, total: 0 });
      agg.total++; if (isCorrect) agg.correct++;
      review.push({
        question_id: q.id, is_correct: isCorrect,
        selected_option_ids: selected.slice().sort(),
        correct_option_ids: correctIds.slice().sort(),
        explanation: q.explanation, domain: q.domain,
      });
    });
    var total = review.length;
    var byDomainArr = Object.keys(dom).sort().map(function (k) {
      return { domain: k, correct: dom[k].correct, total: dom[k].total, rate: dom[k].total ? r4(dom[k].correct / dom[k].total) : 0 };
    });
    return { score: total ? r4(correctCount / total) : 0, correct: correctCount, total: total, by_domain: byDomainArr, review: review };
  }

  // --- Maitrise (EMA), SM-2, second ordre (purs : l'appelant persiste) ---
  function updateMastery(prevScore, prevAttempts, isCorrect) {
    var alpha = 0.2, y = isCorrect ? 1.0 : 0.0;
    if (!prevAttempts) return { score: y, attempts: 1 };
    return { score: prevScore * (1 - alpha) + y * alpha, attempts: prevAttempts + 1 };
  }
  function sm2(card, quality) {
    var ef = card ? card.ease_factor : 2.5;
    var reps = card ? card.repetitions : 0;
    var interval = card ? card.interval_days : 0;
    if (quality < 3) { reps = 0; interval = 1; }
    else {
      reps += 1;
      if (reps === 1) interval = 1;
      else if (reps === 2) interval = 6;
      else interval = Math.round(interval * ef);
      ef = Math.max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)));
    }
    var due = new Date(Date.now() + interval * 86400000).toISOString().slice(0, 10);
    return { ease_factor: ef, interval_days: interval, repetitions: reps, due_date: due };
  }
  function logistic(x) { if (x <= -60) return 0; if (x >= 60) return 1; return 1 / (1 + Math.exp(-x)); }
  function secondOrderUpdate(ability, diff, isCorrect) {
    ability = ability || 0; diff = diff || 0;
    var p = logistic(ability - diff), y = isCorrect ? 1.0 : 0.0, delta = ELO_K * (y - p);
    return { ability: Math.max(-4, Math.min(4, ability + delta)), diff: Math.max(-4, Math.min(4, diff - delta)) };
  }

  // --- Calibration metacognitive (Brier, ECE, courbe, par domaine, tendance) ---
  function brierOf(seq) {
    var s = 0; seq.forEach(function (r) { s += Math.pow(r.predicted - r.is_correct, 2); });
    return s / seq.length;
  }
  function computeBrierTrend(logs, maxBuckets, minBucket) {
    maxBuckets = maxBuckets || 8; minBucket = minBucket || 5;
    var rows = logs.slice(); var n = rows.length;
    if (n < 2 * minBucket) return { available: false, n: n, buckets: [], direction: null };
    var nb = Math.min(maxBuckets, Math.max(2, Math.floor(n / minBucket)));
    var baseSz = Math.floor(n / nb), rem = n % nb, idx = 0, buckets = [];
    for (var k = 0; k < nb; k++) {
      var size = baseSz + (k < rem ? 1 : 0);
      var chunk = rows.slice(idx, idx + size); idx += size;
      buckets.push({ i: k + 1, n: chunk.length, brier: r4(brierOf(chunk)) });
    }
    var half = Math.floor(n / 2);
    var bf = brierOf(rows.slice(0, half)), bs = brierOf(rows.slice(half));
    var delta = bs - bf;
    var direction = delta < -0.02 ? "amelioration" : (delta > 0.02 ? "degradation" : "stable");
    return { available: true, n: n, buckets: buckets, first_half_brier: r4(bf), second_half_brier: r4(bs), delta: r4(delta), direction: direction };
  }
  function computeCalibration(logs) {
    var rows = logs.slice(); var n = rows.length;
    if (n === 0) return { available: false, n: 0, calibration_factor: 1.0, applies: false };
    var brier = brierOf(rows);
    var meanPred = rows.reduce(function (s, r) { return s + r.predicted; }, 0) / n;
    var meanAcc = rows.reduce(function (s, r) { return s + r.is_correct; }, 0) / n;
    var edges = [[0, 0.40, "<40 %"], [0.40, 0.60, "~50 %"], [0.60, 0.85, "~75 %"], [0.85, 1.01, "~95 %"]];
    var ece = 0, bins = [];
    edges.forEach(function (e) {
      var sub = rows.filter(function (r) { return r.predicted >= e[0] && r.predicted < e[1]; });
      if (sub.length) {
        var p = sub.reduce(function (s, x) { return s + x.predicted; }, 0) / sub.length;
        var a = sub.reduce(function (s, x) { return s + x.is_correct; }, 0) / sub.length;
        ece += (sub.length / n) * Math.abs(p - a);
        bins.push({ label: e[2], n: sub.length, predicted: r4(p), actual: r4(a) });
      } else bins.push({ label: e[2], n: 0, predicted: null, actual: null });
    });
    var per = {};
    rows.forEach(function (r) {
      var a = per[r.domain] || (per[r.domain] = { n: 0, pred: 0, acc: 0 });
      a.n++; a.pred += r.predicted; a.acc += r.is_correct;
    });
    var perDomain = Object.keys(per).sort().map(function (k) {
      var v = per[k], mp = v.pred / v.n, ma = v.acc / v.n;
      return { domain: k, n: v.n, predicted: r4(mp), actual: r4(ma), gap: r4(mp - ma) };
    });
    var applies = n >= CALIB_MIN_RECORDS;
    var factor = applies ? Math.max(CALIB_FLOOR, 1.0 - ece) : 1.0;
    return {
      available: true, n: n, brier: r4(brier), mean_predicted: r4(meanPred), mean_actual: r4(meanAcc),
      gap: r4(meanPred - meanAcc), ece: r4(ece), calibration_factor: r4(factor), applies: applies,
      min_records: CALIB_MIN_RECORDS, bins: bins, per_domain: perDomain, trend: computeBrierTrend(rows),
    };
  }

  // --- Preparation (readiness) + recommandations ---
  function computeReadiness(masteryByCode, totalAttempts, opts) {
    opts = opts || {};
    var secondOrder = !!opts.secondOrder;
    var weighted = 0, perDomain = [], weak = [];
    DOMAINS.forEach(function (d) {
      var m = masteryByCode[d.code] || { score: 0, attempts: 0 };
      weighted += m.score * d.weight;
      perDomain.push({ code: d.code, label: d.label, weight: r4(d.weight), mastery: r4(m.score), attempts: m.attempts || 0 });
      if (m.score < DOMAIN_FLOOR) weak.push(d.code);
    });
    var dataConfidence = Math.min(1.0, totalAttempts / DATA_CONFIDENCE_THRESHOLD);
    var readinessRaw = weighted * dataConfidence;
    var factor = (secondOrder && opts.calibration) ? opts.calibration.calibration_factor : 1.0;
    var readiness = readinessRaw * factor;
    return {
      readiness: r4(readiness), readiness_raw: r4(readinessRaw), raw_mastery: r4(weighted),
      confidence: r4(dataConfidence), calibration_factor: r4(factor), second_order: secondOrder,
      total_attempts: totalAttempts, per_domain: perDomain, weak_domains: weak,
    };
  }
  function buildRecommendations(readiness, target) {
    var recs = [], weak = readiness.weak_domains;
    if (readiness.total_attempts < 20) recs.push("Commencez par quelques sessions d'entrainement pour fiabiliser l'estimation de preparation.");
    weak.forEach(function (c) { recs.push("Renforcez le domaine " + c + " (maitrise sous le seuil de 65 %)."); });
    if (readiness.readiness >= target && weak.length === 0) recs.push("Objectif atteint : vous etes pret. Enchainez un examen blanc en conditions reelles pour confirmer.");
    else if (weak.length === 0 && readiness.readiness < target) recs.push("Vous etes au-dessus du seuil de passage sur tous les domaines : poussez vers votre cible avec le mode intensif.");
    if (recs.length === 0) recs.push("Poursuivez l'entrainement regulier et planifiez un examen blanc.");
    return recs;
  }

  return {
    CERT_CODE: CERT_CODE, QUESTION_COUNT: QUESTION_COUNT, PASS_THRESHOLD: PASS_THRESHOLD, DURATION_MIN: DURATION_MIN,
    TARGET_MIN: TARGET_MIN, TARGET_MAX: TARGET_MAX, TARGET_DEFAULT: TARGET_DEFAULT,
    DOMAIN_FLOOR: DOMAIN_FLOOR, CONFIDENCE_CHOICES: CONFIDENCE_CHOICES,
    DOMAINS: DOMAINS, DOMAIN_CODES: DOMAIN_CODES, DOMAIN_LABEL: DOMAIN_LABEL,
    LEVEL_BANDS: LEVEL_BANDS, LEVEL_LABEL: LEVEL_LABEL, EXAM_PRESETS: EXAM_PRESETS,
    loadBank: loadBank, byDomain: byDomain, computeQuotas: computeQuotas,
    generateExam: generateExam, buildBandExams: buildBandExams, presetInfo: presetInfo, presetExam: presetExam,
    gradeAnswers: gradeAnswers, updateMastery: updateMastery, sm2: sm2,
    logistic: logistic, secondOrderUpdate: secondOrderUpdate,
    computeBrierTrend: computeBrierTrend, computeCalibration: computeCalibration,
    computeReadiness: computeReadiness, buildRecommendations: buildRecommendations,
    mulberry32: mulberry32,
  };
});
