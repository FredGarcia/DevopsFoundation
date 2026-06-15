// taskpane.js — Logique du complément Word "Reprise DEX -> CAST'IN".
//
// Étapes :
//   1. Attendre que Office.js soit prêt (Office.onReady).
//   2. Au clic sur "Analyser ce DEX" :
//        a. Récupérer le document Word ouvert au format .docx compressé
//           (Office.context.document.getFileAsync), tranche par tranche.
//        b. Concaténer les tranches puis encoder en base64.
//        c. POST vers le service local dex_castin_word_addin_server.py
//           (http://127.0.0.1:8943/api/process-dex).
//        d. Afficher les trois blocs de résultat (identification, champs
//           CAST'IN, points à vérifier), avec un bouton "copier" par champ.
//
// Le service local applique exactement les mêmes règles que le script
// autonome dex_castin_cli.py (module commun dex_castin_common.py) : aucune
// règle métier n'est dupliquée ici, ce fichier ne fait que transport + affichage.

const SERVICE_URL = "http://127.0.0.1:8943/api/process-dex";

Office.onReady(() => {
  document.getElementById("run-button").addEventListener("click", runDexExtraction);
});

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

async function runDexExtraction() {
  setStatus("Lecture du document Word...");
  document.getElementById("result").innerHTML = "";

  try {
    const docxBytes = await getDocumentAsCompressedBytes();
    const docxBase64 = bytesToBase64(docxBytes);

    setStatus("Analyse du DEX par le service local...");
    const response = await fetch(SERVICE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: (Office.context.document.url || "DEX.docx").split(/[\\/]/).pop(),
        docx_base64: docxBase64,
      }),
    });

    if (!response.ok) {
      const errPayload = await response.json().catch(() => ({}));
      throw new Error(errPayload.error || `Erreur HTTP ${response.status}`);
    }

    const data = await response.json();
    renderResult(data);
    setStatus("Terminé.");
  } catch (err) {
    setStatus(`Erreur : ${err.message}. Le service local est-il démarré (port 8943) ?`);
  }
}

/**
 * Récupère le document Word ouvert au format .docx (compressé), en
 * assemblant les tranches renvoyées par Office.js.
 * @returns {Promise<Uint8Array>}
 */
function getDocumentAsCompressedBytes() {
  return new Promise((resolve, reject) => {
    Office.context.document.getFileAsync(Office.FileType.Compressed, { sliceSize: 65536 }, (result) => {
      if (result.status !== Office.AsyncResultStatus.Succeeded) {
        reject(new Error(result.error.message));
        return;
      }

      const file = result.value;
      const sliceCount = file.sliceCount;
      const slices = new Array(sliceCount);
      let received = 0;

      const getSlice = (index) => {
        file.getSliceAsync(index, (sliceResult) => {
          if (sliceResult.status !== Office.AsyncResultStatus.Succeeded) {
            file.closeAsync();
            reject(new Error(sliceResult.error.message));
            return;
          }
          slices[index] = sliceResult.value.data; // Uint8Array (ou tableau de nombres)
          received += 1;
          if (received === sliceCount) {
            file.closeAsync();
            const total = slices.reduce((sum, s) => sum + s.length, 0);
            const merged = new Uint8Array(total);
            let offset = 0;
            for (const slice of slices) {
              merged.set(slice, offset);
              offset += slice.length;
            }
            resolve(merged);
          } else {
            getSlice(index + 1);
          }
        });
      };

      if (sliceCount === 0) {
        file.closeAsync();
        resolve(new Uint8Array());
      } else {
        getSlice(0);
      }
    });
  });
}

/** Encode un Uint8Array en base64 sans dépasser la taille d'appel de String.fromCharCode. */
function bytesToBase64(bytes) {
  const CHUNK = 0x8000;
  let result = "";
  for (let i = 0; i < bytes.length; i += CHUNK) {
    result += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(result);
}

/** Affiche le résultat structuré renvoyé par le service. */
function renderResult(data) {
  const root = document.getElementById("result");
  root.innerHTML = "";

  // 1. Identification
  const ident = data.identification || {};
  root.appendChild(
    section("1. Identification", [
      ["Solution", ident.solution || "Non concerné"],
      ["Auteur", ident.auteur || "Non concerné"],
      ["Responsable", ident.responsable || "Non concerné"],
    ])
  );

  // 2. Champs CAST'IN
  const champsDiv = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = "2. Contenu par champ CAST'IN";
  champsDiv.appendChild(h2);

  for (const key of Object.keys(data.champs || {})) {
    const champ = data.champs[key];
    champsDiv.appendChild(fieldBlock(champ.label, champ.content));
  }
  root.appendChild(champsDiv);

  // 3. Points à vérifier
  const points = data.points_a_verifier || [];
  const pointsDiv = document.createElement("div");
  const h3 = document.createElement("h3");
  h3.textContent = "3. Points à vérifier auprès de l'Équipier Ops";
  pointsDiv.appendChild(h3);

  const list = document.createElement("div");
  list.className = "points";
  if (points.length === 0) {
    list.textContent = "RAS";
  } else {
    const ul = document.createElement("ul");
    for (const p of points) {
      const li = document.createElement("li");
      li.textContent = p;
      ul.appendChild(li);
    }
    list.appendChild(ul);
  }
  pointsDiv.appendChild(list);
  root.appendChild(pointsDiv);
}

function section(title, pairs) {
  const div = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = title;
  div.appendChild(h2);
  for (const [label, value] of pairs) {
    div.appendChild(fieldBlock(label, value));
  }
  return div;
}

function fieldBlock(label, content) {
  const div = document.createElement("div");
  div.className = "field";

  const labelEl = document.createElement("div");
  labelEl.className = "field-label";
  labelEl.textContent = label;

  const copyBtn = document.createElement("button");
  copyBtn.className = "copy-btn";
  copyBtn.textContent = "Copier";
  copyBtn.addEventListener("click", () => navigator.clipboard.writeText(content || ""));
  labelEl.appendChild(copyBtn);

  const contentEl = document.createElement("div");
  contentEl.className = "field-content";
  contentEl.textContent = content && content.length ? content : "(laisser vide)";

  div.appendChild(labelEl);
  div.appendChild(contentEl);
  return div;
}
