// Éditeur de culte : sélection des diapos, ruban, glisser-déposer, dialogues,
// et saisie des chants directement sur la grande diapo (« mode édition »).
//
// Le fragment #espace est remplacé par le serveur après chaque modification
// de structure (HTMX) : `initialiserEspace` est rejoué à chaque fois. La saisie
// du texte, elle, est envoyée en arrière-plan (fetch) sans recharger l'espace,
// pour ne jamais déplacer le curseur pendant qu'on tape.
(function () {
  "use strict";

  let vue = "normal";
  let numeroCourant = 1;
  let edition = ""; // identifiant du chant ouvert en édition
  let minuterie = null;
  let modifie = false;
  let file = Promise.resolve(); // sauvegardes envoyées dans l'ordre
  let plage = null; // dernière sélection de texte dans la diapo (pour la couleur)

  const DELAI_SAUVEGARDE = 700;
  const espace = () => document.getElementById("espace");
  const grande = () => document.getElementById("diapo-grande");
  const zoneEditable = () => grande() && grande().querySelector('.diapo-contenu[contenteditable="true"]');

  function jeton() {
    try {
      return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"];
    } catch (e) {
      return "";
    }
  }

  function urlChant(chant, suite) {
    return `/cultes/${espace().dataset.culte}/chants/${chant}/${suite}`;
  }

  // ------------------------------------------------------------ Sélection

  function selectionner(numero, { focus = false } = {}) {
    const e = espace();
    if (!e) return;
    sauverMaintenant();
    const vignettes = Array.from(e.querySelectorAll(".vignette"));
    const g = grande();
    if (!vignettes.length) {
      g.className = "diapo diapo-grande diapo-vide";
      g.innerHTML = "";
      majRuban(null);
      return;
    }
    numero = Math.min(Math.max(1, numero), vignettes.length);
    const vignette = vignettes[numero - 1];
    vignettes.forEach((v) => v.classList.toggle("active", v === vignette));

    const source = vignette.querySelector(".diapo");
    g.className = source.className + " diapo-grande";
    g.setAttribute("style", source.getAttribute("style") || "");
    g.innerHTML = source.innerHTML;
    g.dataset.piece = vignette.dataset.piece || "";
    g.dataset.chant = vignette.dataset.chant || "";
    g.dataset.alignement = source.dataset.alignement || "centre";
    g.dataset.taille = source.dataset.taille || "";
    g.dataset.taillePt = source.dataset.taillePt || "";
    g.dataset.police = source.dataset.police || "";
    g.dataset.fond = source.dataset.fond || "";

    const editable = edition && g.dataset.piece && g.dataset.chant === edition;
    g.classList.toggle("diapo-editable", !!editable);
    if (editable) {
      const contenu = g.querySelector(".diapo-contenu");
      contenu.contentEditable = "true";
      contenu.spellcheck = true;
      if (!contenu.innerHTML.trim()) contenu.innerHTML = "<div><br></div>";
      if (focus) placerCurseurAlaFin(contenu);
    }

    const position = e.querySelector("[data-position]");
    if (position) position.textContent = numero;

    numeroCourant = numero;
    majRuban(vignette);
    vignette.scrollIntoView({ block: "nearest" });
  }

  function placerCurseurAlaFin(zone) {
    zone.focus();
    const range = document.createRange();
    range.selectNodeContents(zone);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  // Propriétés et actions d'un élément du culte (fenêtre .dlg-proprietes de _espace.html).
  function fenetreProprietes(element) {
    return element ? espace().querySelector(`.dlg-proprietes[data-element="${element}"]`) : null;
  }

  function ouvrirProprietes(element) {
    const fenetre = fenetreProprietes(element);
    if (!fenetre) return;
    fenetre.showModal();
    const champ = fenetre.querySelector("input[name=titre], input[name=moment]");
    if (champ) champ.focus();
  }

  function actionElement(element, action) {
    const fenetre = fenetreProprietes(element);
    const bouton = fenetre && fenetre.querySelector(`[data-action="${action}"]`);
    if (bouton) bouton.click();
  }

  // État des boutons du ruban selon la diapo sélectionnée et le mode édition.
  function majRuban(vignette) {
    const element = vignette ? vignette.dataset.element : "";
    const chant = vignette ? vignette.dataset.chant : "";
    const surPiece = !!(edition && vignette && vignette.dataset.piece && chant === edition);
    document.querySelectorAll("[data-cible]").forEach((b) => (b.disabled = !element || !!edition));
    document.querySelectorAll("[data-en-edition]").forEach((b) => {
      const pourDiapo = b.matches("[data-format], [data-diapo-reglage], [data-couleur-texte], [data-couleur-fond], [data-taille-diapo], [data-police-diapo]")
        || ["dupliquer", "haut", "bas", "supprimer"].includes(b.dataset.diapoAction);
      b.disabled = !edition || (pourDiapo && !surPiece);
    });
    document.querySelectorAll('[data-chant-action="editer"][data-hors-edition]').forEach((b) => (b.disabled = !!edition || !chant));
    afficherReglages();
    document.querySelectorAll("[data-couleur-texte], [data-couleur-fond]").forEach((i) => {
      i.closest("label").classList.toggle("desactive", i.disabled);
    });

    const e = espace();
    document.body.classList.toggle("mode-edition", !!edition);
    if (!e) return;
    e.querySelectorAll(".groupe[data-chant]").forEach((gr) => gr.classList.toggle("groupe-edition", gr.dataset.chant === edition));
    const bandeau = document.getElementById("bandeau-edition");
    if (bandeau) {
      bandeau.hidden = !edition;
      const groupe = edition && e.querySelector(`.groupe[data-chant="${edition}"] .groupe-nom`);
      bandeau.querySelector("[data-titre-edition]").textContent = groupe ? groupe.textContent : "";
    }
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
    if (e.dataset.edition) edition = e.dataset.edition;
    if (edition && !e.querySelector(`.groupe[data-chant="${edition}"]`)) edition = "";

    let numero = numeroCourant;
    let focus = false;
    const piece = e.dataset.piece && e.querySelector(`.vignette[data-piece="${e.dataset.piece}"]`);
    const selection = e.dataset.selection && e.querySelector(`.vignette[data-element="${e.dataset.selection}"]`);
    if (piece) {
      numero = Number(piece.dataset.numero);
      focus = true;
    } else if (selection) {
      numero = Number(selection.dataset.numero);
    }
    selectionner(numero, { focus });

    const liste = e.querySelector(".groupes[data-reordonner]");
    if (liste && window.Sortable && !liste.dataset.triable) {
      liste.dataset.triable = "1";
      Sortable.create(liste, {
        animation: 150,
        draggable: ".groupe",
        handle: ".groupe-entete",
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
    activerTriDiapos();
  }

  // En mode édition, les vignettes du chant se réordonnent par glisser-déposer.
  function activerTriDiapos() {
    const e = espace();
    if (!edition || !e || !window.Sortable) return;
    const groupe = e.querySelector(`.groupe[data-chant="${edition}"]`);
    if (!groupe || groupe.dataset.triDiapos) return;
    groupe.dataset.triDiapos = "1";
    Sortable.create(groupe, {
      animation: 150,
      draggable: ".vignette[data-piece]",
      async onEnd(evt) {
        if (evt.oldIndex === evt.newIndex) return;
        await sauverMaintenant();
        const ordre = Array.from(groupe.querySelectorAll(".vignette[data-piece]")).map((v) => v.dataset.piece);
        htmx.ajax("POST", groupe.dataset.reordonnerDiapos, {
          target: "#espace",
          swap: "outerHTML",
          values: { ordre: ordre, piece: evt.item.dataset.piece },
        });
      },
    });
  }

  // ------------------------------------------------------------ Mode édition

  function ouvrirEdition(chant) {
    if (!chant) return;
    edition = String(chant);
    const e = espace();
    // Se placer sur la première diapo du chant (après la diapo titre).
    const v = e.querySelector(`.vignette[data-chant="${edition}"][data-piece]`) || e.querySelector(`.vignette[data-chant="${edition}"]`);
    selectionner(v ? Number(v.dataset.numero) : numeroCourant, { focus: true });
    activerTriDiapos();
  }

  async function fermerEdition() {
    await sauverMaintenant();
    edition = "";
    const zone = zoneEditable();
    if (zone) zone.blur();
    selectionner(numeroCourant);
  }

  // Copie immédiate du texte saisi dans la vignette (avant la réponse du serveur).
  function majVignette(piece, contenu, reglages) {
    const v = espace().querySelector(`.vignette[data-piece="${piece}"] .diapo`);
    if (!v) return;
    if (contenu !== undefined) v.querySelector(".diapo-contenu").innerHTML = contenu;
    if (reglages) {
      if (reglages.taille) v.style.setProperty("--taille", reglages.taille);
      if (reglages.alignement) {
        v.dataset.alignement = reglages.alignement;
        v.querySelector(".diapo-contenu").className = "diapo-contenu aligner-" + reglages.alignement;
      }
      if (reglages.taille_pt !== undefined) {
        v.dataset.taillePt = reglages.taille_pt;
        v.dataset.taille = reglages.taille_choisie || "";
      }
      if (reglages.police !== undefined) {
        v.dataset.police = reglages.police;
        const pile = pileDe(reglages.police);
        if (pile) v.style.setProperty("--police", pile);
        else v.style.removeProperty("--police");
      }
      if (reglages.couleur_fond !== undefined) {
        v.dataset.fond = reglages.couleur_fond;
        v.style.background = reglages.couleur_fond || "";
      }
    }
  }

  function planifierSauvegarde() {
    modifie = true;
    indiquer("Modification…");
    const zone = zoneEditable();
    if (zone) majVignette(grande().dataset.piece, zone.innerHTML);
    clearTimeout(minuterie);
    minuterie = setTimeout(sauverMaintenant, DELAI_SAUVEGARDE);
  }

  function donneesDiapo() {
    const g = grande();
    const zone = zoneEditable();
    if (!g || !zone || !g.dataset.piece) return null;
    const corps = new FormData();
    corps.append("contenu", zone.innerHTML);
    corps.append("alignement", g.dataset.alignement || "centre");
    corps.append("taille", g.dataset.taille || "");
    corps.append("police", g.dataset.police || "");
    corps.append("couleur_fond", g.dataset.fond || "");
    return { corps, chant: g.dataset.chant, piece: g.dataset.piece };
  }

  function sauverMaintenant() {
    clearTimeout(minuterie);
    if (!modifie) return file;
    modifie = false;
    const envoi = donneesDiapo();
    if (!envoi) return file;
    file = file
      .then(() =>
        fetch(urlChant(envoi.chant, `diapos/${envoi.piece}/`), {
          method: "POST",
          body: envoi.corps,
          headers: { "X-CSRFToken": jeton() },
          credentials: "same-origin",
        })
      )
      .then(async (reponse) => {
        if (!reponse.ok) throw new Error(await reponse.text());
        const d = await reponse.json();
        majVignette(envoi.piece, d.contenu, d);
        const g = grande();
        if (g && g.dataset.piece === envoi.piece) {
          g.style.setProperty("--taille", d.taille);
          g.dataset.taillePt = d.taille_pt;
          afficherReglages();
        }
        indiquerEnregistre();
      })
      .catch((erreur) => {
        modifie = true; // on réessaiera à la prochaine modification
        indiquer("⚠ Non enregistré" + (erreur.message && erreur.message.length < 120 ? " : " + erreur.message : ""), true);
      });
    return file;
  }

  // Réglages de la diapo (taille, alignement, fond) : appliqués tout de suite, puis enregistrés.
  function reglerDiapo(reglage, valeur) {
    const g = grande();
    if (!zoneEditable()) return;
    if (reglage === "plus" || reglage === "moins") {
      // Taille suivante / précédente de la liste du ruban, à partir de la taille affichée.
      const actuelle = Number(g.dataset.taillePt) || 54;
      const tailles = taillesProposees();
      const suivante = reglage === "plus"
        ? tailles.find((t) => t > actuelle) || tailles[tailles.length - 1]
        : [...tailles].reverse().find((t) => t < actuelle) || tailles[0];
      fixerTaille(g, suivante);
    } else if (reglage === "taille") {
      const n = parseInt(valeur, 10);
      if (Number.isNaN(n)) g.dataset.taille = ""; // automatique : le serveur renvoie la taille
      else fixerTaille(g, Math.min(200, Math.max(8, n)));
    } else if (reglage === "police") {
      g.dataset.police = valeur;
      const pile = pileDe(valeur);
      if (pile) g.style.setProperty("--police", pile);
      else g.style.removeProperty("--police");
    } else if (["gauche", "centre", "droite"].includes(reglage)) {
      g.dataset.alignement = reglage;
      g.querySelector(".diapo-contenu").classList.remove("aligner-gauche", "aligner-centre", "aligner-droite");
      g.querySelector(".diapo-contenu").classList.add("aligner-" + reglage);
    } else if (reglage === "fond") {
      g.dataset.fond = valeur;
      g.style.background = valeur;
    } else if (reglage === "fond-theme") {
      g.dataset.fond = "";
      g.style.background = "";
    }
    majVignette(g.dataset.piece, undefined, {
      alignement: g.dataset.alignement,
      couleur_fond: g.dataset.fond,
      police: g.dataset.police || "",
      taille: g.style.getPropertyValue("--taille") || undefined,
      taille_pt: g.dataset.taillePt,
      taille_choisie: g.dataset.taille,
    });
    afficherReglages();
    modifie = true;
    sauverMaintenant();
  }

  function fixerTaille(g, points) {
    g.dataset.taille = String(points);
    g.dataset.taillePt = String(points);
    g.style.setProperty("--taille", (points * 100 / 960).toFixed(3) + "cqw"); // comme rendu.en_cqw
  }

  function taillesProposees() {
    return Array.from(document.querySelectorAll("#tailles-pt option")).map((o) => Number(o.value));
  }

  function pileDe(police) {
    const option = police && document.querySelector(`[data-police-diapo] option[value="${CSS.escape(police)}"]`);
    return option ? option.dataset.pile : "";
  }

  // Le ruban montre la police, la taille et l'alignement de la diapo affichée.
  function afficherReglages() {
    const g = grande();
    const avecTexte = !!(g && g.dataset.piece);
    const champTaille = document.querySelector("[data-taille-diapo]");
    if (champTaille && document.activeElement !== champTaille) {
      champTaille.value = avecTexte ? g.dataset.taillePt || "" : "";
      champTaille.classList.toggle("taille-auto", avecTexte && !g.dataset.taille);
    }
    const choixPolice = document.querySelector("[data-police-diapo]");
    if (choixPolice) choixPolice.value = avecTexte ? g.dataset.police || "" : "";
    document.querySelectorAll('[data-diapo-reglage="gauche"], [data-diapo-reglage="centre"], [data-diapo-reglage="droite"]').forEach((b) => {
      const actif = avecTexte && (g.dataset.alignement || "centre") === b.dataset.diapoReglage;
      b.classList.toggle("outil-actif", actif);
      b.setAttribute("aria-pressed", actif ? "true" : "false");
    });
  }

  async function actionDiapo(action) {
    const g = grande();
    const chant = edition;
    if (!chant) return;
    await sauverMaintenant();
    const piece = g.dataset.chant === chant ? g.dataset.piece : "";
    const options = { target: "#espace", swap: "outerHTML" };
    if (action === "ajouter") {
      htmx.ajax("POST", urlChant(chant, "diapos/ajouter/"), { ...options, values: { apres: piece } });
    } else if (!piece) {
      return;
    } else if (action === "dupliquer") {
      htmx.ajax("POST", urlChant(chant, "diapos/ajouter/"), { ...options, values: { dupliquer: piece } });
    } else if (action === "haut" || action === "bas") {
      htmx.ajax("POST", urlChant(chant, `diapos/${piece}/deplacer/`), { ...options, values: { sens: action } });
    } else if (action === "supprimer") {
      if (!window.confirm("Supprimer cette diapo du chant ?")) return;
      htmx.ajax("POST", urlChant(chant, `diapos/${piece}/supprimer/`), options);
    }
  }

  function formater(commande, valeur) {
    const zone = zoneEditable();
    if (!zone) return;
    if (plage && document.activeElement !== zone) {
      zone.focus();
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(plage);
    }
    document.execCommand("styleWithCSS", false, false);
    document.execCommand(commande, false, valeur || null);
    planifierSauvegarde();
  }

  // ------------------------------------------------------------ Saisie

  document.addEventListener("input", (evt) => {
    if (evt.target.closest && evt.target.closest('#diapo-grande .diapo-contenu[contenteditable="true"]')) {
      planifierSauvegarde();
    }
  });

  // Coller : texte seul (la mise en forme de Word ou d'une page web est ignorée).
  document.addEventListener("paste", (evt) => {
    if (!evt.target.closest || !evt.target.closest('#diapo-grande .diapo-contenu[contenteditable="true"]')) return;
    evt.preventDefault();
    const texte = (evt.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, texte);
  });

  document.addEventListener("selectionchange", () => {
    const zone = zoneEditable();
    const sel = window.getSelection();
    if (zone && sel.rangeCount && zone.contains(sel.anchorNode)) plage = sel.getRangeAt(0).cloneRange();
  });

  // Les boutons de mise en forme ne doivent pas faire perdre la sélection du texte.
  document.addEventListener("mousedown", (evt) => {
    if (evt.target.closest("[data-format], [data-diapo-reglage]")) evt.preventDefault();
  });

  document.addEventListener("input", (evt) => {
    if (evt.target.matches && evt.target.matches("[data-couleur-texte]")) formater("foreColor", evt.target.value);
    if (evt.target.matches && evt.target.matches("[data-couleur-fond]")) reglerDiapo("fond", evt.target.value);
  });

  // Taille saisie (validée par Entrée ou en quittant le champ) et police choisie.
  document.addEventListener("change", (evt) => {
    if (!evt.target.matches) return;
    if (evt.target.matches("[data-taille-diapo]")) reglerDiapo("taille", evt.target.value);
    if (evt.target.matches("[data-police-diapo]")) reglerDiapo("police", evt.target.value);
  });
  document.addEventListener("keydown", (evt) => {
    if (evt.key === "Enter" && evt.target.matches && evt.target.matches("[data-taille-diapo]")) {
      evt.preventDefault();
      // Retour dans la diapo : la perte du focus déclenche « change », donc l'enregistrement.
      const zone = zoneEditable();
      if (zone) placerCurseurAlaFin(zone);
      else evt.target.blur();
    }
  });

  // Dernière chance d'envoyer une saisie en cours si on quitte la page.
  window.addEventListener("pagehide", () => {
    if (!modifie) return;
    const envoi = donneesDiapo();
    if (!envoi) return;
    envoi.corps.append("csrfmiddlewaretoken", jeton());
    navigator.sendBeacon(urlChant(envoi.chant, `diapos/${envoi.piece}/`), envoi.corps);
  });

  // ------------------------------------------------------------ Clics

  function ouvrirDialogue(id) {
    const dialogue = document.getElementById(id);
    if (!dialogue) return;
    document.querySelectorAll("dialog[open]").forEach((d) => d !== dialogue && d.close());
    const erreur = dialogue.querySelector("[data-erreur]");
    if (erreur) erreur.hidden = true;
    dialogue.showModal();
    const champ = dialogue.querySelector("input[type=search], input[name=titre], textarea, input:not([type=hidden])");
    if (champ) champ.focus();
  }

  document.addEventListener("click", (evt) => {
    const cible = evt.target.closest("button, a");
    if (!cible) return;

    if (cible.classList.contains("vignette")) {
      selectionner(Number(cible.dataset.numero), { focus: !!edition });
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
      const active = espace().querySelector(".vignette.active");
      if (cible.dataset.cible === "proprietes") ouvrirProprietes(active && active.dataset.element);
      else actionElement(active && active.dataset.element, cible.dataset.cible);
      return;
    }
    if (cible.dataset.chantAction === "editer") {
      const active = espace().querySelector(".vignette.active");
      ouvrirEdition(cible.dataset.chant || (active && active.dataset.chant));
      return;
    }
    if (cible.dataset.chantAction === "fermer") {
      fermerEdition();
      return;
    }
    if (cible.dataset.format) {
      formater(cible.dataset.format);
      return;
    }
    if (cible.dataset.diapoReglage) {
      reglerDiapo(cible.dataset.diapoReglage);
      return;
    }
    if (cible.dataset.diapoAction) {
      actionDiapo(cible.dataset.diapoAction);
      return;
    }
    if (cible.dataset.dialogue) {
      ouvrirDialogue(cible.dataset.dialogue);
      return;
    }
    if (cible.hasAttribute("data-fermer")) {
      cible.closest("dialog").close();
    }
  });

  // Double-clic sur une diapo de chant : l'ouvrir en édition (ou, dans la
  // trieuse, revenir en vue normale sur cette diapo).
  document.addEventListener("dblclick", (evt) => {
    const entete = evt.target.closest(".groupe-entete");
    if (entete && !edition) {
      ouvrirProprietes(entete.closest(".groupe").dataset.element);
      return;
    }
    const vignette = evt.target.closest(".vignette");
    if (!vignette) return;
    if (vue === "trieuse") {
      vue = "normal";
      appliquerVue();
      selectionner(Number(vignette.dataset.numero));
    } else if (vignette.dataset.chant && !edition && document.querySelector("[data-format]")) {
      ouvrirEdition(vignette.dataset.chant);
      selectionner(Number(vignette.dataset.numero), { focus: true });
    }
  });

  document.addEventListener("keydown", (evt) => {
    const dansDiapo = evt.target.closest && evt.target.closest('[contenteditable="true"]');
    if (edition && (dansDiapo || !evt.target.closest("input, textarea, select, dialog[open]"))) {
      if (evt.key === "Enter" && (evt.ctrlKey || evt.metaKey)) {
        evt.preventDefault();
        actionDiapo("ajouter");
        return;
      }
      if (evt.key === "Escape") {
        evt.preventDefault();
        fermerEdition();
        return;
      }
    }
    if (dansDiapo || evt.target.closest("input, textarea, select, dialog[open]")) return;
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

  function indiquerEnregistre() {
    const heure = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    indiquer("✓ Enregistré à " + heure);
  }

  document.addEventListener("htmx:beforeRequest", (evt) => {
    if (evt.detail.requestConfig.verb === "post") indiquer("Enregistrement…");
  });

  document.addEventListener("htmx:afterRequest", (evt) => {
    if (evt.detail.requestConfig.verb !== "post") return;
    const source = evt.detail.elt;
    if (evt.detail.successful) {
      indiquerEnregistre();
      if (source.hasAttribute && source.hasAttribute("data-ferme-apres")) {
        const dialogue = source.closest("dialog");
        if (dialogue) dialogue.close();
        if (source.tagName === "FORM") source.reset();
      }
      if (source.classList && source.classList.contains("form-titre")) {
        document.title = source.elements.titre.value + " · Danzapa";
      }
      // Après l'ajout d'un chant, le moment suivant n'est plus « Cantique d'entrée ».
      if (source.classList && source.classList.contains("resultat")) {
        const moment = document.getElementById("moment-chant");
        if (moment) moment.value = "";
      }
    } else {
      const message = evt.detail.xhr && evt.detail.xhr.responseText;
      const court = message && message.length < 200 ? message : "";
      indiquer("⚠ Non enregistré" + (court ? " : " + court : ""), true);
      const zoneErreur = source.closest && source.closest("dialog") && source.closest("dialog").querySelector("[data-erreur]");
      if (zoneErreur) {
        zoneErreur.textContent = court || "Une erreur est survenue.";
        zoneErreur.hidden = false;
      }
    }
  });

  document.addEventListener("htmx:sendError", () => indiquer("⚠ Connexion perdue, non enregistré", true));

  document.addEventListener("DOMContentLoaded", () => {
    document.execCommand("defaultParagraphSeparator", false, "div");
    initialiserEspace();
    htmx.onLoad((elt) => {
      if (elt.id === "espace") initialiserEspace();
    });
  });
})();
