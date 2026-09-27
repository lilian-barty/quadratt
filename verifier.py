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
  7. Rien de ce qui arrive de l'extérieur n'est glissé tel quel dans la page.
     Ajouté le 27/09/2026, après une faille restée trois jours en ligne : un
     nom de case piégé, écrit sur un tableau Trello, s'exécutait dans le
     navigateur du propriétaire et pouvait lire son jeton. Quatre vérifications :
       a. le modèle d'axes est nettoyé à son entrée (assainirModele appelé en
          tête d'appliquerModele) ;
       b. l'adresse d'une carte ne finit dans un lien qu'à travers lienCarte(),
          seule barrière contre un fichier carnet importé et piégé ;
       c. dans un gabarit qui produit du HTML, un champ venu de Trello ou du
          carnet (name, desc, list, tableauNom) passe par esc() ;
       d. quand le script tourne dans le dépôt du site, la politique de
          sécurité servie avec /quadratt/ n'autorise d'envoi que vers Trello.
     Limite connue : une valeur qui transite par une variable intermédiaire
     avant d'atteindre le gabarit échappe au contrôle c. Il attrape la
     régression ordinaire, pas une construction faite pour le contourner.
"""

import io, json, os, re, sys, html as H

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


# --- découpage du JavaScript en gabarits -----------------------------------
# Une expression régulière ne suffit pas à trouver les gabarits `...` : le
# code en contient d'imbriqués (`<b>${x ? `<i>${y}</i>` : ""}</b>`), et au
# moins une expression régulière du script contient elle-même un accent
# grave. On parcourt donc le code en sautant chaînes, commentaires et
# expressions régulières, comme le ferait le navigateur.

MOTS_AVANT_REGEX = {'return', 'typeof', 'case', 'in', 'of', 'delete', 'void',
                    'throw', 'new', 'instanceof', 'else', 'do', 'yield', 'await'}
PONCT_AVANT_REGEX = set('(,=:[!&|?{};+-*%<>~^')


def gabarits_du_script(js):
    """Rend, pour chaque gabarit du script, son texte littéral et la liste de
       ses expressions ${...}. Chaque expression est rendue en squelette : les
       chaînes y sont remplacées par "", les gabarits imbriqués par ``, qui
       sont eux-mêmes rendus à part."""
    trouves = []
    n = len(js)

    def fin_chaine(i, q):
        i += 1
        while i < n:
            c = js[i]
            if c == '\\':
                i += 2
                continue
            if c == q or c == '\n':
                return i + 1
            i += 1
        return i

    def fin_regex(i):
        i += 1
        classe = False
        while i < n:
            c = js[i]
            if c == '\\':
                i += 2
                continue
            if c == '\n':
                return i
            if classe:
                if c == ']':
                    classe = False
            elif c == '[':
                classe = True
            elif c == '/':
                i += 1
                while i < n and js[i].isalpha():
                    i += 1
                return i
            i += 1
        return i

    def lire_gabarit(i):
        i += 1
        texte, exprs = [], []
        while i < n:
            c = js[i]
            if c == '\\':
                texte.append(js[i:i + 2])
                i += 2
                continue
            if c == '`':
                trouves.append((''.join(texte), exprs))
                return i + 1
            if c == '$' and js[i + 1:i + 2] == '{':
                i, squelette = lire_code(i + 2, jusqua_accolade=True)
                exprs.append(squelette)
                continue
            texte.append(c)
            i += 1
        return i

    def lire_code(i, jusqua_accolade=False):
        prof, sq, prec, mot = 0, [], '', ''
        while i < n:
            c = js[i]
            if c in ' \t\r\n':
                sq.append(c)
                i += 1
                continue
            if c == '/' and js[i + 1:i + 2] == '/':
                j = js.find('\n', i)
                i = n if j < 0 else j
                continue
            if c == '/' and js[i + 1:i + 2] == '*':
                j = js.find('*/', i + 2)
                i = n if j < 0 else j + 2
                continue
            if c == '/' and (prec == '' or prec in PONCT_AVANT_REGEX or mot in MOTS_AVANT_REGEX):
                i = fin_regex(i)
                sq.append('RE')
                prec, mot = 'x', ''
                continue
            if c in '"\'':
                i = fin_chaine(i, c)
                sq.append('""')
                prec, mot = 'x', ''
                continue
            if c == '`':
                i = lire_gabarit(i)
                sq.append('``')
                prec, mot = 'x', ''
                continue
            if jusqua_accolade:
                if c == '{':
                    prof += 1
                elif c == '}':
                    if prof == 0:
                        return i + 1, ''.join(sq)
                    prof -= 1
            if c.isalnum() or c in '_$':
                j = i
                while j < n and (js[j].isalnum() or js[j] in '_$'):
                    j += 1
                mot = js[i:j]
                sq.append(mot)
                prec = 'x'
                i = j
                continue
            sq.append(c)
            prec, mot = c, ''
            i += 1
        return i, ''.join(sq)

    lire_code(0)
    return trouves


def retirer_appels(expr, nom):
    """Remplace chaque appel nom(...) par un jeton neutre, parenthèses
       équilibrées comprises : ce qui est dedans est réputé protégé."""
    motif = re.compile(r'\b' + nom + r'\(')
    while True:
        m = motif.search(expr)
        if not m:
            return expr
        i, prof = m.end(), 1
        while i < len(expr) and prof:
            prof += {'(': 1, ')': -1}.get(expr[i], 0)
            i += 1
        expr = expr[:m.start()] + '_' + expr[i:]


# Champs dont la valeur arrive de Trello ou d'un fichier carnet, donc de
# n'importe qui. Les textes du modèle d'axes n'y figurent pas : ils sont
# nettoyés à leur entrée, et c'est justement ce que vérifie le contrôle 7a.
CHAMP_EXTERIEUR = re.compile(r'\.(name|desc|list)\b|\btableauNom\b')
CHAMP_ADRESSE = re.compile(r'\.(url|shortUrl)\b')

# Un champ extérieur qui sert à choisir ou à comparer n'arrive pas à l'écran :
# lists.filter(l => l.name !== "Fait") n'affiche aucun nom. Ces appels
# rendent un booléen, un rang ou un tri, jamais le texte lui-même. Ce qui
# suit l'appel reste contrôlé : lists.find(...).name est bien attrapé.
APPELS_SANS_AFFICHAGE = ('filter', 'find', 'findIndex', 'some', 'every', 'test',
                         'includes', 'indexOf', 'has', 'sort')
COMPARAISON = re.compile(r'[\w.$\[\]]+\s*[!=]==?\s*[\w.$\[\]"\']+')


def part_affichee(expr):
    for nom in ('esc', 'lienCarte') + APPELS_SANS_AFFICHAGE:
        expr = retirer_appels(expr, nom)
    return COMPARAISON.sub('_', expr)


def controle_textes_exterieurs(h):
    titre(7, "Textes venus de l'extérieur")
    scripts = re.findall(r'<script(?![^>]*ld\+json)[^>]*>(.*?)</script>', h, re.S)
    gabs = [g for s in scripts for g in gabarits_du_script(s)]

    # a. le modèle est nettoyé à son entrée
    m = re.search(r'function appliquerModele\([^)]*\)\s*\{', h)
    ok_a = bool('function assainirModele(' in h and m
                and 'assainirModele(' in h[m.end():m.end() + 200])
    if not ok_a:
        print("     appliquerModele() ne commence plus par assainirModele()")
    verdict(ok_a, 'modèle d’axes nettoyé à son entrée')

    # b. l'adresse d'une carte passe par lienCarte()
    adresses = []
    for texte, exprs in gabs:
        if '<' not in texte:
            continue
        for e in exprs:
            if CHAMP_ADRESSE.search(retirer_appels(e, 'lienCarte')):
                adresses.append(' '.join(e.split()))
    for e in re.findall(r'window\.open\(\s*([\w.]+)', h):
        if CHAMP_ADRESSE.search(e):
            adresses.append('window.open(' + e)
    for e in adresses:
        print('     ${%s} : adresse de carte hors de lienCarte()' % e[:70])
    verdict('function lienCarte(' in h and not adresses,
            '%d adresse(s) de carte non filtrée(s)' % len(adresses))

    # c. champs extérieurs échappés dans les gabarits HTML
    nus = []
    for texte, exprs in gabs:
        if '<' not in texte:
            continue
        for e in exprs:
            if CHAMP_EXTERIEUR.search(part_affichee(e)):
                nus.append(' '.join(e.split()))
    for e in nus:
        print('     ${%s} : texte extérieur affiché sans esc()' % e[:70])
    verdict(not nus, '%d texte(s) extérieur(s) non échappé(s) dans %d gabarit(s) HTML'
            % (len(nus), sum(1 for t_, _ in gabs if '<' in t_)))

    # d. politique de sécurité servie avec la page
    vj = os.path.join(os.path.dirname(os.path.abspath(FICHIER)), '..', 'vercel.json')
    if not os.path.exists(vj):
        print("   --   politique de sécurité non vérifiée : pas de vercel.json à côté")
        return
    conf = json.load(io.open(vj, encoding='utf-8'))
    csp = [x['value'] for r in conf.get('headers', []) if r.get('source', '').startswith('/quadratt')
           for x in r.get('headers', []) if x.get('key', '').lower() == 'content-security-policy']
    csp = csp[0] if csp else ''
    ok_d = bool(csp and "default-src 'none'" in csp
                and re.search(r"connect-src https://api\.trello\.com\s*(;|$)", csp)
                and 'unsafe-eval' not in csp)
    if not csp:
        print('     aucune Content-Security-Policy pour /quadratt/ dans vercel.json')
    elif not ok_d:
        print('     la politique autorise plus que Trello : ' + csp[:90])
    verdict(ok_d, 'envois limités à Trello par la politique de sécurité')


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

    # --- 7. textes venus de l'extérieur ------------------------------------
    controle_textes_exterieurs(h)

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
