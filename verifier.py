"""
Vérification de Quadratt — à lancer depuis le dossier du projet :

    python verifier.py

Ne modifie rien, ne fait que rapporter. Sort en code 1 si un contrôle échoue,
pour pouvoir être branché sur autre chose un jour.

Ce fichier existe parce que le LISEZ-MOI prévoyait de « réécrire au besoin »
un script d'audit à chaque session : le réécrire, c'est le refaire faux une
fois sur deux. Les pièges déjà rencontrés sont encodés ici une bonne fois.

CE QU'IL VÉRIFIE
  1. Toute clé passée à t() ou tf() existe dans le bon dictionnaire.
     Piège : t() ne lit que EN, tf() lit EN et EN_MODELES. Ranger une clé
     dans le mauvais dictionnaire laisse du français à l'écran.
  2. Aucune clé morte dans EN.
     Pièges : le texte du HTML peut être coupé sur plusieurs lignes, contenir
     des entités (&amp;), des espaces fines posées par typo(). On compare donc
     sur une forme normalisée, sinon on supprime des clés bien vivantes.
  3. Aucune clé en double.
  4. Aucune classe CSS sans cible.
     Piège : beaucoup de classes naissent dans des gabarits JS, parfois
     construites (class="ech${...}"). Les faux positifs connus sont listés.
  5. Aucune couleur en dur dans le CSS hors du bloc :root.
     Sans ça, le mode sombre laisse des plaques claires.
  6. Le mode sombre définit bien les mêmes variables que le mode clair.
     Le bloc étant écrit deux fois (requête média + attribut), il dérive vite.
"""

import io, re, sys, html as H

# La console Windows sort en cp1252 par défaut et mange les accents.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Un chemin peut être passé en argument, pour vérifier une copie sans toucher
# au fichier de travail.
FICHIER = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
ECHECS = []

# faux positifs connus, vérifiés à la main le 30/07/2026
CLASSES_TOLEREES = {
    'ech',    # construite en gabarit : class="ech${e.retard?" retard":""}"
    'woff2',  # vient des url(...) de @font-face, ce n'est pas une classe
}


def lire():
    return io.open(FICHIER, encoding='utf-8').read()


def normaliser(s):
    """Ce que voit chercherEN() : entités décodées, espaces fines ramenées à
       l'espace simple, retours à la ligne écrasés."""
    s = H.unescape(s)
    s = s.replace(' ', ' ').replace(' ', ' ')
    s = s.replace('\\n', ' ').replace('\\"', '"')
    return re.sub(r'\s+', ' ', s).strip()


def bornes(h, nom):
    i = h.find('const ' + nom + ' = {')
    if i < 0:
        raise SystemExit('Dictionnaire %s introuvable.' % nom)
    return i, h.find('\n};', i)


def titre(n, texte):
    print()
    print('%s. %s' % (n, texte))
    print('   ' + '-' * (len(texte) + 1))


def verdict(ok, message):
    print('   %s %s' % ('OK  ' if ok else 'ECHEC', message))
    if not ok:
        ECHECS.append(message)


def main():
    h = lire()
    CHAINE = r'"((?:[^"\\]|\\.)*)"'

    i_en, j_en = bornes(h, 'EN')
    i_mod, j_mod = bornes(h, 'EN_MODELES')
    EN, MOD = h[i_en:j_en], h[i_mod:j_mod]
    hors_dico = h[:i_en] + h[j_en:i_mod] + h[j_mod:]

    cles_en = re.findall(r'^\s*' + CHAINE + r'\s*:', EN, re.M)
    cles_mod = re.findall(r'^\s*' + CHAINE + r'\s*:', MOD, re.M)
    print('Quadratt — vérification')
    print('=======================')
    print('EN : %d clés   EN_MODELES : %d clés' % (len(cles_en), len(cles_mod)))

    # --- 1. clés appelées mais absentes ---------------------------------
    titre(1, 'Clés appelées par t() / tf()')
    appels_t = set(re.findall(r'\bt\(\s*' + CHAINE, hors_dico))
    appels_tf = set(re.findall(r'\btf\(\s*' + CHAINE, hors_dico))
    manque_t = sorted(k for k in appels_t if k not in cles_en)
    manque_tf = sorted(k for k in appels_tf if k not in cles_en and k not in cles_mod)
    for k in manque_t:
        print('     t("%s") : absente de EN' % k[:70])
    for k in manque_tf:
        print('     tf("%s") : absente des deux dictionnaires' % k[:70])
    verdict(not manque_t and not manque_tf,
            '%d appel(s) sans traduction' % (len(manque_t) + len(manque_tf)))

    # --- 1 bis. textes du HTML ------------------------------------------
    # traduireArbre() traduit les nœuds de texte et trois attributs. Ces
    # chaînes ne passent PAS par t() : sans ce contrôle, retirer « Bilan » du
    # dictionnaire ne déclenche aucune alerte et le bouton reste en français
    # sur l'interface anglaise. C'est la fuite la plus fréquente du projet.
    titre('1bis', 'Textes du HTML traduits par traduireArbre')
    html_seul = h[:h.find('<script>')]
    html_seul = re.sub(r'<!--.*?-->', ' ', html_seul, flags=re.S)
    html_seul = re.sub(r'<style>.*?</style>', ' ', html_seul, flags=re.S)
    html_seul = re.sub(r'<svg[^>]*>.*?</svg>', ' ', html_seul, flags=re.S)
    # le bloc de données structurées n'est pas de l'interface : il porte un
    # type à lui, donc il échappe au découpage sur le premier <script> nu
    html_seul = re.sub(r'<script[^>]*>.*?</script>', ' ', html_seul, flags=re.S)

    attendus = set()
    for a in ('placeholder', 'title', 'aria-label'):
        attendus |= set(re.findall(a + r'="([^"]+)"', html_seul))
    for morceau in re.split(r'<[^>]+>', html_seul):
        m = normaliser(morceau)
        if len(m) > 2 and re.search(r'[A-Za-zÀ-ÿ]{3}', m):
            attendus.add(m)

    connues = {normaliser(k) for k in cles_en} | {normaliser(k) for k in cles_mod}
    # Ce qui n'a pas à figurer au dictionnaire : marques et noms propres, plus
    # les libellés que le script pose lui-même dans les deux langues.
    IGNORE = {'Quadratt', 'Trello', 'Lilian Barty-Christophe', 'FR', 'EN',
              'Ctrl+Z', 'Google', 'Microsoft', 'Atlassian',
              'Changer de langue'}   # posé par majBoutonLangue(), pas traduit ici
    sans_trad = sorted(t for t in attendus
                       if t not in connues and t not in IGNORE
                       and not t.startswith('http')
                       and not re.fullmatch(r'[IVXLC]+', t))   # chiffres romains
    for t_ in sans_trad:
        print('     "%s"' % t_[:80])
    verdict(not sans_trad, '%d texte(s) du HTML sans traduction' % len(sans_trad))

    # --- 2. clés mortes --------------------------------------------------
    titre(2, 'Clés jamais utilisées')
    reste_n = normaliser(hors_dico)
    mortes = [k for k in sorted(set(cles_en))
              if normaliser(k) and normaliser(k) not in reste_n]
    for k in mortes:
        print('     "%s"' % k[:70])
    verdict(not mortes, '%d clé(s) morte(s) dans EN' % len(mortes))

    # --- 3. doublons -----------------------------------------------------
    titre(3, 'Clés en double')
    doubles = []
    for bloc, nom in ((cles_en, 'EN'), (cles_mod, 'EN_MODELES')):
        vus = {}
        for k in bloc:
            vus[k] = vus.get(k, 0) + 1
        for k, n in vus.items():
            if n > 1:
                doubles.append('%s : "%s" x%d' % (nom, k[:60], n))
    for d in doubles:
        print('     ' + d)
    verdict(not doubles, '%d clé(s) en double' % len(doubles))

    # --- 4. classes CSS sans cible ---------------------------------------
    titre(4, 'Classes CSS sans cible')
    d1, d2 = h.find('<style>'), h.rfind('</style>')
    css, hors_css = h[d1:d2], h[:d1] + h[d2:]
    orphelines = []
    for c in sorted(set(re.findall(r'\.([A-Za-z][\w-]*)', css))):
        if c in CLASSES_TOLEREES or c in hors_css:
            continue
        orphelines.append(c)
    for c in orphelines:
        print('     .%s' % c)
    verdict(not orphelines, '%d classe(s) sans cible' % len(orphelines))

    # --- 5. couleurs en dur ----------------------------------------------
    titre(5, 'Couleurs en dur dans le CSS')
    k = css.find(':root{')
    fin_root = css.find('}', k)
    css_hors_root = css[:k] + css[fin_root:]
    # les palettes de thème sont des blocs de variables, on les saute aussi
    css_hors_root = re.sub(r':root(?:\[[^\]]+\])?(?::not\([^)]*\))?\{[^}]*\}', ' ', css_hors_root)
    css_hors_root = re.sub(r'@media[^{]*\{\s*:root[^{]*\{[^}]*\}\s*\}', ' ', css_hors_root)
    dures = []
    for m in re.finditer(r'(?:background|color|border[\w-]*|fill|stroke|box-shadow)\s*:[^;{}]*?(#[0-9A-Fa-f]{3,8})', css_hors_root):
        dures.append(m.group(0).strip()[:70])
    for d in sorted(set(dures)):
        print('     ' + d)
    verdict(not dures, '%d couleur(s) en dur hors des palettes' % len(set(dures)))

    # --- 6. cohérence des deux palettes sombres --------------------------
    titre(6, 'Les deux écritures du mode sombre')
    blocs = re.findall(r':root(?::not\(\[data-theme="clair"\]\))?(?:\[data-theme="sombre"\])?\s*\{([^}]*)\}', css)
    palettes = [set(re.findall(r'(--[\w-]+)\s*:', b)) for b in blocs if '--papier' in b]
    if len(palettes) >= 3:
        clair, sombre1, sombre2 = palettes[0], palettes[1], palettes[2]
        ecart = sombre1 ^ sombre2
        for v in sorted(ecart):
            print('     %s : présente dans une écriture seulement' % v)
        oubli = sorted((clair - sombre1) - {'--sans', '--serif', '--t'})
        for v in oubli:
            print('     %s : définie en clair, jamais en sombre' % v)
        verdict(not ecart and not oubli,
                '%d écart(s) entre les palettes' % (len(ecart) + len(oubli)))
    else:
        verdict(False, 'palettes introuvables (%d bloc(s) trouvé(s))' % len(palettes))

    # --- bilan -----------------------------------------------------------
    print()
    print('=======================')
    if ECHECS:
        print('%d CONTROLE(S) EN ECHEC' % len(ECHECS))
        for e in ECHECS:
            print('  - ' + e)
        sys.exit(1)
    print('Tout est vert.')


if __name__ == '__main__':
    main()
