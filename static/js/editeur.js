// Éditeur de culte : sélection des diapos, ruban, glisser-déposer, dialogues.
// Le fragment #espace est remplacé par le serveur après chaque modification
// (HTMX) : `initialiserEspace` est rejoué à chaque fois.
(function () {
  "use strict";

  let vue = "normal";
  let numeroCourant = 1;

  const espace = () => document.getElementById("espace");

  function selectionner(numero) {
    const e = espace();
    if (!e) return;
    const vignettes = Array.from(e.querySelectorAll(".vignette"));
    const grande = document.getElementById("diapo-grande");
    if (!vignettes.length) {
      grande.className = "diapo diapo-grande diapo-vide";
      grande.innerHTML = "";
      e.querySelectorAll(".proprietes").forEach((p) => (p.hidden = true));
      majActionsRuban(null);
      return;
    }
    numero = Math.min(Math.max(1, numero), vignettes.length);
    const vignette = vignettes[numero - 1];
    vignettes.forEach((v) => v.classList.toggle("active", v === vignette));

    const source = vignette.querySelector(".diapo");
    grande.className = source.className + " diapo-grande";
    grande.setAttribute("style", source.getAttribute("style") || "");
    grande.innerHTML = source.innerHTML;

    const position = e.querySelector("[data-position]");
    if (position) position.textContent = numero;

    const element = vignette.dataset.element;
    e.querySelectorAll(".proprietes").forEach((p) => (p.hidden = p.dataset.element !== element));
    majActionsRuban(element);

    numeroCourant = numero;
    vignette.scrollIntoView({ block: "nearest" });
  }

  // Les boutons « Élément sélectionné » du ruban déclenchent ceux du panneau
  // de propriétés visible ; ils sont désactivés sur la diapo de bienvenue.
  function majActionsRuban(element) {
    document.querySelectorAll("[data-cible]").forEach((b) => (b.disabled = !element));
  }

  function appliquerVue() {
    const e = espace();
    if (e) e.classList.toggle("vue-trieuse", vue === "trieuse");
    document.querySelectorAll("[data-vue]").forEach((b) => b.classList.toggle("actif", b.dataset.vue === vue));
  }

  function initialiserEspace() {
    const e = espace();
    if (!e) return;
    appliquerVue();

    let numero = numeroCourant;
    const selection = e.dataset.selection;
    if (selection) {
      const v = e.querySelector(`.vignette[data-element="${selection}"]`);
      if (v) numero = Number(v.dataset.numero);
    }
    selectionner(numero);

    const liste = e.querySelector(".groupes[data-reordonner]");
    if (liste && window.Sortable && !liste.dataset.triable) {
      liste.dataset.triable = "1";
      Sortable.create(liste, {
        animation: 150,
        draggable: ".groupe",
        onEnd(evt) {
          if (evt.oldIndex === evt.newIndex) return;
          const ordre = Array.from(liste.querySelectorAll(".groupe")).map((g) => g.dataset.element);
          const active = e.querySelector(".vignette.active");
          htmx.ajax("POST", liste.dataset.reordonner, {
            target: "#espace",
            swap: "outerHTML",
            values: { ordre: ordre, selection: active ? active.dataset.element : "" },
          });
        },
      });
    }
  }

  // ------------------------------------------------------------ Clics

  document.addEventListener("click", (evt) => {
    const cible = evt.target.closest("button, a");
    if (!cible) return;

    if (cible.classList.contains("vignette")) {
      selectionner(Number(cible.dataset.numero));
      return;
    }

    if (cible.dataset.onglet) {
      document.querySelectorAll("[data-onglet]").forEach((b) => b.classList.toggle("actif", b === cible));
      document.querySelectorAll("[data-panneau]").forEach((p) => (p.hidden = p.dataset.panneau !== cible.dataset.onglet));
      return;
    }

    if (cible.dataset.vue) {
      vue = cible.dataset.vue;
      appliquerVue();
      selectionner(numeroCourant);
      return;
    }

    if (cible.dataset.cible) {
      const bouton = espace().querySelector(`.proprietes:not([hidden]) [data-action="${cible.dataset.cible}"]`);
      if (bouton) bouton.click();
      return;
    }

    if (cible.dataset.dialogue) {
      const dialogue = document.getElementById(cible.dataset.dialogue);
      if (dialogue) {
        dialogue.showModal();
        const champ = dialogue.querySelector("input[type=search], textarea, input:not([type=hidden])");
        if (champ) champ.focus();
      }
      return;
    }

    if (cible.hasAttribute("data-fermer")) {
      cible.closest("dialog").close();
      return;
    }

    // « Saisir un nouveau chant » : garder le moment déjà choisi.
    if (cible.hasAttribute("data-avec-moment")) {
      const moment = document.getElementById("moment-chant");
      if (moment && moment.value) {
        evt.preventDefault();
        window.location = cible.href + "?moment=" + encodeURIComponent(moment.value);
      }
    }
  });

  // Double-clic dans la trieuse : revenir en vue normale sur cette diapo.
  document.addEventListener("dblclick", (evt) => {
    const vignette = evt.target.closest(".vignette");
    if (vignette && vue === "trieuse") {
      vue = "normal";
      appliquerVue();
      selectionner(Number(vignette.dataset.numero));
    }
  });

  // Flèches, Page préc./suiv., Début/Fin : naviguer entre les diapos.
  document.addEventListener("keydown", (evt) => {
    if (evt.target.closest("input, textarea, select, dialog[open]")) return;
    const pas = { ArrowDown: 1, ArrowRight: 1, PageDown: 1, ArrowUp: -1, ArrowLeft: -1, PageUp: -1 }[evt.key];
    if (pas) {
      evt.preventDefault();
      selectionner(numeroCourant + pas);
    } else if (evt.key === "Home") {
      selectionner(1);
    } else if (evt.key === "End") {
      selectionner(Infinity);
    }
  });

  // ------------------------------------------------------------ HTMX

  function indiquer(texte, erreur) {
    const indicateur = document.getElementById("indicateur");
    if (!indicateur) return;
    indicateur.textContent = texte;
    indicateur.classList.toggle("indicateur-erreur", !!erreur);
  }

  document.addEventListener("htmx:beforeRequest", (evt) => {
    if (evt.detail.requestConfig.verb === "post") indiquer("Enregistrement…");
  });

  document.addEventListener("htmx:afterRequest", (evt) => {
    if (evt.detail.requestConfig.verb !== "post") return;
    if (evt.detail.successful) {
      const heure = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      indiquer("✓ Enregistré à " + heure);
      const source = evt.detail.elt;
      if (source.hasAttribute("data-ferme-apres")) {
        const dialogue = source.closest("dialog");
        if (dialogue) dialogue.close();
        if (source.tagName === "FORM") source.reset();
      }
      if (source.classList.contains("form-titre")) {
        document.title = source.elements.titre.value + " · Danzapa";
      }
      // Après l'ajout d'un chant, le moment suivant n'est plus « Cantique d'entrée ».
      if (source.classList.contains("resultat")) {
        const moment = document.getElementById("moment-chant");
        if (moment) moment.value = "";
      }
    } else {
      const message = evt.detail.xhr && evt.detail.xhr.responseText;
      indiquer("⚠ Non enregistré" + (message && message.length < 200 ? " : " + message : ""), true);
    }
  });

  document.addEventListener("htmx:sendError", () => indiquer("⚠ Connexion perdue, non enregistré", true));

  document.addEventListener("DOMContentLoaded", () => {
    initialiserEspace();
    htmx.onLoad((elt) => {
      if (elt.id === "espace") initialiserEspace();
    });
  });
})();
