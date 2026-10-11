"""Animations d'entrée du texte dans le .pptx (onglet Animations de PowerPoint).

python-pptx ne gère pas les animations : on écrit le bloc XML <p:timing> de la
diapo, comme PowerPoint pour un effet d'entrée « Après la précédente » sur la
première animation (il démarre donc seul, dès l'arrivée sur la diapo).

  fondu   → Fondu            (presetID 10)
  monter  → Balayer, du bas  (presetID 22)
  zoom    → Zoom simple      (presetID 53)
  lignes  → Fondu, paragraphe après paragraphe
  machine → Fondu (pas d'équivalent fiable lettre par lettre)
"""

from pptx.oxml import parse_xml

NS = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
DUREES_MS = {"rapide": 400, "normale": 800, "lente": 1500}


class _Compteur:
    def __init__(self, depart):
        self.valeur = depart

    def __call__(self):
        self.valeur += 1
        return self.valeur


def _cible(spid, paragraphe=None):
    if paragraphe is None:
        return f'<p:spTgt spid="{spid}"/>'
    return f'<p:spTgt spid="{spid}"><p:txEl><p:pRg st="{paragraphe}" end="{paragraphe}"/></p:txEl></p:spTgt>'


def _visible(cid, cible):
    return (
        f'<p:set><p:cBhvr><p:cTn id="{cid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        f'<p:tgtEl>{cible}</p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
        '<p:to><p:strVal val="visible"/></p:to></p:set>'
    )


def _filtre(cid, cible, filtre, duree):
    return (
        f'<p:animEffect transition="in" filter="{filtre}"><p:cBhvr><p:cTn id="{cid()}" dur="{duree}"/>'
        f'<p:tgtEl>{cible}</p:tgtEl></p:cBhvr></p:animEffect>'
    )


def _agrandir(cid, cible, attribut, duree):
    return (
        f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{cid()}" dur="{duree}" fill="hold"/>'
        f'<p:tgtEl>{cible}</p:tgtEl><p:attrNameLst><p:attrName>{attribut}</p:attrName></p:attrNameLst></p:cBhvr>'
        '<p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav>'
        f'<p:tav tm="100000"><p:val><p:strVal val="#{attribut}"/></p:val></p:tav></p:tavLst></p:anim>'
    )


def _effet(cid, animation, cible, duree):
    """(presetID, presetSubtype, comportements XML) d'un effet d'entrée."""
    if animation == "monter":
        return 22, 4, _visible(cid, cible) + _filtre(cid, cible, "wipe(up)", duree)
    if animation == "zoom":
        return 53, 16, (
            _visible(cid, cible)
            + _agrandir(cid, cible, "ppt_w", duree)
            + _agrandir(cid, cible, "ppt_h", duree)
            + _filtre(cid, cible, "fade", duree)
        )
    return 10, 0, _visible(cid, cible) + _filtre(cid, cible, "fade", duree)


def animer(diapositive, forme, animation, vitesse="normale", nb_paragraphes=1):
    """Ajoute l'animation d'entrée `animation` (DiapoChant.ANIMATIONS) à la zone de texte `forme`."""
    if not animation:
        return
    duree = DUREES_MS.get(vitesse, DUREES_MS["normale"])
    spid = forme.shape_id
    cid = _Compteur(2)  # 1 : racine, 2 : séquence principale
    par_paragraphe = animation == "lignes"
    cibles = [_cible(spid, i) for i in range(nb_paragraphes)] if par_paragraphe else [_cible(spid)]
    effet_de_base = "fondu" if animation in ("lignes", "machine") else animation

    groupes = []
    for rang, cible in enumerate(cibles):
        id_groupe, id_sous_groupe = cid(), cid()
        id_effet = cid()
        preset, sous_type, comportements = _effet(cid, effet_de_base, cible, duree)
        # Le premier effet attend le début de la séquence ; les suivants enchaînent.
        depart = (
            '<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>'
            if rang == 0 else '<p:cond delay="indefinite"/>'
        )
        groupes.append(
            f'<p:par><p:cTn id="{id_groupe}" fill="hold"><p:stCondLst>{depart}</p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{id_sous_groupe}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{id_effet}" presetID="{preset}" presetClass="entr" presetSubtype="{sous_type}" '
            f'fill="hold" grpId="0" nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
            f'<p:childTnLst>{comportements}</p:childTnLst></p:cTn></p:par>'
            '</p:childTnLst></p:cTn></p:par>'
            '</p:childTnLst></p:cTn></p:par>'
        )
    construction = f'<p:bldP spid="{spid}" grpId="0" build="p"/>' if par_paragraphe else f'<p:bldP spid="{spid}" grpId="0"/>'
    xml = (
        f'<p:timing {NS}><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        + "".join(groupes)
        + '</p:childTnLst></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        '</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
        f'<p:bldLst>{construction}</p:bldLst></p:timing>'
    )
    racine = diapositive._element
    ancien = racine.find("{http://schemas.openxmlformats.org/presentationml/2006/main}timing")
    if ancien is not None:
        racine.remove(ancien)
    # Ordre du schéma : cSld, clrMapOvr, transition, timing, extLst.
    extension = racine.find("{http://schemas.openxmlformats.org/presentationml/2006/main}extLst")
    timing = parse_xml(xml)
    if extension is not None:
        extension.addprevious(timing)
    else:
        racine.append(timing)
