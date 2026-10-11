// Lecture des animations d'entrée du texte (data-animation d'une .diapo).
// Utilisé par la projection, la vue présentateur et l'aperçu de l'éditeur.
(() => {
  "use strict";

  const DUREES = { rapide: 0.4, normale: 0.8, lente: 1.5 };

  // Machine à écrire : chaque caractère dans un <span class="lettre"> avec son
  // délai. Seuls les nœuds texte sont découpés : gras, couleurs… sont conservés.
  function preparerMachine(contenu, duree) {
    const textes = [];
    const parcours = document.createTreeWalker(contenu, NodeFilter.SHOW_TEXT);
    while (parcours.nextNode()) textes.push(parcours.currentNode);
    const total = textes.reduce((n, t) => n + t.data.length, 0) || 1;
    // Durée totale : la vitesse choisie, rallongée selon la longueur du texte.
    const pas = Math.max(duree * 2, total * 0.035 * (duree / 0.8)) / total;
    let rang = 0;
    textes.forEach((noeud) => {
      const morceaux = document.createDocumentFragment();
      for (const c of noeud.data) {
        const lettre = document.createElement("span");
        lettre.className = "lettre";
        lettre.textContent = c;
        lettre.style.setProperty("--delai", `${(rang++ * pas).toFixed(3)}s`);
        morceaux.appendChild(lettre);
      }
      noeud.replaceWith(morceaux);
    });
  }

  // Remet le texte d'origine (avant un nouveau découpage, ou avant l'édition).
  function nettoyer(diapo) {
    const contenu = diapo.querySelector(".diapo-contenu");
    if (contenu && contenu.dataset.original !== undefined) {
      contenu.innerHTML = contenu.dataset.original;
      delete contenu.dataset.original;
    }
    diapo.classList.remove("joue");
  }

  // Joue l'animation de la diapo ; renvoie sa durée totale en secondes (0 sans animation).
  function jouerAnimation(diapo) {
    if (!diapo) return 0;
    nettoyer(diapo);
    const animation = diapo.dataset.animation;
    if (!animation) return 0;
    const contenu = diapo.querySelector(".diapo-contenu");
    if (!contenu) return 0;
    const duree = DUREES[diapo.dataset.vitesse] || DUREES.normale;
    let total = duree;
    if (animation === "lignes") {
      const lignes = Array.from(contenu.children);
      lignes.forEach((ligne, i) => ligne.style.setProperty("--rang", i));
      total = duree + duree * 0.5 * Math.max(lignes.length - 1, 0);
    } else if (animation === "machine") {
      contenu.dataset.original = contenu.innerHTML;
      preparerMachine(contenu, duree);
      const lettres = contenu.querySelectorAll(".lettre");
      const derniere = lettres[lettres.length - 1];
      total = (derniere ? parseFloat(derniere.style.getPropertyValue("--delai")) : 0) + 0.05;
    }
    void diapo.offsetWidth; // relance l'animation CSS même si la classe était déjà là
    diapo.classList.add("joue");
    return total;
  }

  window.danzapaAnimations = { jouerAnimation, nettoyer };
})();
