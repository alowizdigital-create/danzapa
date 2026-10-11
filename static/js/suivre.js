// « Suivre le culte » : taille du texte et mode clair / sombre, retenus sur le téléphone.
(() => {
  "use strict";
  const TAILLES = [0.95, 1.05, 1.15, 1.3, 1.45, 1.65, 1.9];
  const lire = (cle, defaut) => {
    try {
      return localStorage.getItem(cle) ?? defaut;
    } catch (e) {
      return defaut;
    }
  };
  const ecrire = (cle, valeur) => {
    try {
      localStorage.setItem(cle, valeur);
    } catch (e) {
      /* navigation privée : sans mémoire, tant pis */
    }
  };

  let rang = Number(lire("danzapa-suivre-taille", 2));
  const appliquerTaille = () => {
    rang = Math.max(0, Math.min(TAILLES.length - 1, rang));
    document.documentElement.style.setProperty("--taille", TAILLES[rang] + "rem");
    document.body.style.setProperty("--taille", TAILLES[rang] + "rem");
  };
  const appliquerMode = () => document.body.classList.toggle("clair", lire("danzapa-suivre-mode", "sombre") === "clair");

  document.addEventListener("click", (evt) => {
    const taille = evt.target.closest("[data-taille]");
    if (taille) {
      rang += Number(taille.dataset.taille);
      appliquerTaille();
      ecrire("danzapa-suivre-taille", rang);
    }
    if (evt.target.closest("[data-mode]")) {
      ecrire("danzapa-suivre-mode", document.body.classList.contains("clair") ? "sombre" : "clair");
      appliquerMode();
    }
    if (evt.target.closest("[data-actualiser]")) window.location.reload();
  });

  appliquerTaille();
  appliquerMode();
})();
