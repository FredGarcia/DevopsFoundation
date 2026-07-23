/* Persistance locale (navigateur) — aucune donnee ne quitte l'appareil.
 * Stocke preferences, maitrise par domaine, cartes SM-2, journal de confiance,
 * difficulte latente, aptitude, total de tentatives et historique d'examens.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DOFStore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var KEY = "dofprep:v1";

  function fresh() {
    return {
      v: 1,
      prefs: { target_score: 0.90, second_order: false, agent_url: "http://127.0.0.1:8799" },
      mastery: {},          // code -> {score, attempts}
      cards: {},            // qid  -> {ease_factor, interval_days, repetitions, due_date}
      confidence: [],       // [{predicted, is_correct, domain, context, ts}]
      theta_ability: 0.0,
      theta_item: {},       // qid -> latent difficulty override
      attempts_total: 0,
      history: [],          // [{ts, kind, score, correct, total, label}]
    };
  }

  var state;
  try {
    var raw = (typeof localStorage !== "undefined") ? localStorage.getItem(KEY) : null;
    state = raw ? JSON.parse(raw) : fresh();
  } catch (e) { state = fresh(); }

  // Migration douce : complete les champs de preferences ajoutes apres la
  // premiere version, sans jamais ecraser une valeur deja personnalisee.
  if (!state.prefs) state.prefs = {};
  if (state.prefs.target_score == null) state.prefs.target_score = 0.90;
  if (state.prefs.second_order == null) state.prefs.second_order = false;
  if (!state.prefs.agent_url) state.prefs.agent_url = "http://127.0.0.1:8799";

  function persist() {
    try { if (typeof localStorage !== "undefined") localStorage.setItem(KEY, JSON.stringify(state)); }
    catch (e) { /* quota / mode prive : on ignore proprement */ }
  }
  function reset() { state = fresh(); persist(); }

  return {
    get state() { return state; },
    persist: persist,
    reset: reset,
    KEY: KEY,
  };
});
