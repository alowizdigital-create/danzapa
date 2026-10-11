// Ouverture de la fenêtre « projecteur » sur le second écran (vidéoprojecteur).
// Partagé par l'éditeur et la vue présentateur.
(() => {
  "use strict";

  const NOM_FENETRE = "danzapa-projecteur";

  // Écran du projecteur : un écran autre que celui de cette fenêtre (mode « étendre »).
  // API Window Management (Chrome, Edge) ; ailleurs, ou sans autorisation : null.
  async function ecranDuProjecteur() {
    if (!("getScreenDetails" in window)) return null;
    try {
      const details = await window.getScreenDetails();
      return details.screens.find((e) => e !== details.currentScreen) || null;
    } catch (erreur) {
      return null; // autorisation « Gestion des fenêtres » refusée
    }
  }

  // Ouvre (ou réutilise) la fenêtre projecteur. Renvoie la fenêtre, ou null si
  // le navigateur a bloqué la popup.
  async function ouvrirProjecteur(adresse) {
    const url = new URL(adresse, window.location.href);
    url.searchParams.set("projecteur", "1");
    const ecran = await ecranDuProjecteur();
    let options = "popup";
    if (ecran) {
      options += `,fullscreen,left=${ecran.availLeft},top=${ecran.availTop},width=${ecran.availWidth},height=${ecran.availHeight}`;
    } else {
      options += ",width=960,height=540";
    }
    const fenetre = window.open(url.href, NOM_FENETRE, options);
    // Le clavier doit rester à la vue présentateur (au mieux : certains navigateurs l'ignorent).
    window.focus();
    return fenetre;
  }

  window.danzapaEcrans = { ouvrirProjecteur };
})();
