// Projection d'un culte (plein écran) et vue présentateur.
// Les deux fenêtres d'un même culte restent synchronisées via BroadcastChannel.
(() => {
  "use strict";

  const corps = document.body;
  const presentateur = corps.dataset.mode === "presentateur";
  const diapos = Array.from(document.querySelectorAll("[data-diapo]"));
  const total = diapos.length;
  const canal = "BroadcastChannel" in window ? new BroadcastChannel(corps.dataset.canal) : null;

  let index = Math.min(Number(corps.dataset.debut) || 0, Math.max(total - 1, 0));
  let ecran = ""; // "", "noir" ou "blanc"
  let saisie = ""; // numéro tapé au clavier

  function afficher() {
    if (presentateur) afficherPresentateur();
    else afficherProjection();
  }

  function afficherProjection() {
    diapos.forEach((d, i) => (d.hidden = i !== index));
    const fin = document.querySelector("[data-fin]");
    if (fin) fin.hidden = index < total;
    const voile = document.querySelector("[data-ecran]");
    if (voile) {
      voile.hidden = !ecran;
      voile.className = "projection-ecran" + (ecran ? " ecran-" + ecran : "");
    }
  }

  function copier(cadre, source) {
    if (!cadre) return;
    const diapo = source && source.querySelector(".diapo");
    cadre.innerHTML = diapo ? diapo.outerHTML : '<div class="diapo diapo-vide"><div class="diapo-contenu"><p>Fin</p></div></div>';
  }

  function afficherPresentateur() {
    copier(document.querySelector("[data-actuelle]"), diapos[index]);
    copier(document.querySelector("[data-suivante]"), diapos[index + 1]);
    diapos.forEach((d, i) => d.classList.toggle("active", i === index));
    if (diapos[index]) diapos[index].scrollIntoView({ block: "nearest", inline: "nearest" });
    const position = document.querySelector("[data-position]");
    if (position) position.textContent = Math.min(index + 1, total);
    const nom = document.querySelector("[data-nom]");
    if (nom) nom.textContent = diapos[index] ? diapos[index].dataset.nom : "Fin du diaporama";
    document.querySelectorAll("[data-ecran-bouton]").forEach((b) => b.classList.toggle("outil-actif", b.dataset.ecranBouton === ecran));
  }

  function aller(nouvel, { diffuser = true } = {}) {
    index = Math.max(0, Math.min(nouvel, total)); // total = écran de fin
    ecran = "";
    afficher();
    if (diffuser) envoyer();
  }

  function basculerEcran(couleur) {
    ecran = ecran === couleur ? "" : couleur;
    afficher();
    envoyer();
  }

  function envoyer() {
    if (canal) canal.postMessage({ type: "etat", index, ecran });
  }

  if (canal) {
    canal.onmessage = (evt) => {
      const m = evt.data || {};
      if (m.type === "etat") {
        index = Math.max(0, Math.min(Number(m.index) || 0, total));
        ecran = m.ecran || "";
        afficher();
      } else if (m.type === "demande" && presentateur) {
        envoyer(); // une fenêtre de projection vient de s'ouvrir
      }
    };
    if (!presentateur) canal.postMessage({ type: "demande" });
  }

  function pleinEcran() {
    const aide = document.querySelector("[data-aide]");
    if (aide) aide.hidden = true;
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  function quitter() {
    if (document.fullscreenElement) document.exitFullscreen();
    else window.location.href = corps.dataset.retour;
  }

  document.addEventListener("keydown", (evt) => {
    if (evt.ctrlKey || evt.metaKey || evt.altKey) return;
    const touche = evt.key;
    if (/^[0-9]$/.test(touche)) {
      saisie += touche;
      return;
    }
    if (touche === "Enter" && saisie) {
      aller(Number(saisie) - 1);
      saisie = "";
      evt.preventDefault();
      return;
    }
    saisie = "";
    const actions = {
      ArrowRight: () => aller(index + 1),
      ArrowDown: () => aller(index + 1),
      PageDown: () => aller(index + 1),
      " ": () => aller(index + 1),
      Enter: () => aller(index + 1),
      ArrowLeft: () => aller(index - 1),
      ArrowUp: () => aller(index - 1),
      PageUp: () => aller(index - 1),
      Backspace: () => aller(index - 1),
      Home: () => aller(0),
      End: () => aller(total - 1),
      b: () => basculerEcran("noir"),
      B: () => basculerEcran("noir"),
      ".": () => basculerEcran("noir"),
      w: () => basculerEcran("blanc"),
      W: () => basculerEcran("blanc"),
      ",": () => basculerEcran("blanc"),
      f: () => !presentateur && pleinEcran(),
      F: () => !presentateur && pleinEcran(),
      Escape: quitter,
    };
    if (actions[touche]) {
      evt.preventDefault();
      actions[touche]();
    }
  });

  document.addEventListener("click", (evt) => {
    if (presentateur) {
      const vignette = evt.target.closest("[data-diapo]");
      if (vignette) return aller(Number(vignette.dataset.index));
      const bouton = evt.target.closest("[data-aller]");
      if (bouton) return aller(index + (bouton.dataset.aller === "suivante" ? 1 : -1));
      const ecranBouton = evt.target.closest("[data-ecran-bouton]");
      if (ecranBouton) return basculerEcran(ecranBouton.dataset.ecranBouton);
      if (evt.target.closest("[data-chrono]")) return (debutChrono = Date.now());
      if (evt.target.closest("[data-ouvrir-projection]")) {
        const url = `${corps.dataset.projection}?depuis=1`;
        window.open(url, "danzapa-projection", "popup,width=960,height=540");
      }
      return;
    }
    // Premier clic : plein écran ; ensuite, un clic passe à la diapo suivante.
    const aide = document.querySelector("[data-aide]");
    if (aide && !aide.hidden) return pleinEcran();
    aller(index + 1);
  });

  // Projection : le curseur disparaît après 2 s d'immobilité.
  if (!presentateur) {
    let minuterie;
    document.addEventListener("mousemove", () => {
      corps.classList.remove("curseur-cache");
      clearTimeout(minuterie);
      minuterie = setTimeout(() => corps.classList.add("curseur-cache"), 2000);
    });
  }

  // Présentateur : chronomètre.
  let debutChrono = Date.now();
  const chrono = document.querySelector("[data-chrono]");
  if (chrono) {
    setInterval(() => {
      const s = Math.floor((Date.now() - debutChrono) / 1000);
      const h = Math.floor(s / 3600);
      const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      chrono.textContent = (h ? h + ":" : "") + mm + ":" + ss;
    }, 1000);
  }

  afficher();
})();
