# Quadratt

Trier ses sujets en quatre cases, et savoir enfin par quoi commencer.

**L'outil en ligne : [lilian-barty.fr/quadratt](https://www.lilian-barty.fr/quadratt/)**, gratuit, sans compte.

Vous avez quarante cartes dans un tableau Trello et aucune idée de laquelle attaquer. Quadratt vous les montre une par une, vous pose deux questions (c'est urgent ? ça a de l'impact ?), et range chaque sujet dans l'une des quatre cases. Ensuite, « Je fais quoi ? » vous sort trois sujets à traiter maintenant, les retards d'abord. Les deux axes se changent, si urgence et impact ne sont pas les bonnes questions pour vous.

## Deux façons de s'en servir

- **Avec Trello** : vous choisissez un tableau, Quadratt trie ses cartes et écrit le classement sous forme d'étiquettes. Le tri reste donc visible dans Trello, même sans l'outil.
- **Sans compte** : un carnet local, pour qui n'a pas Trello. Les sujets restent dans votre navigateur.

En français et en anglais.

## Ce que Quadratt ne fait pas

Il ne collecte rien. Pas de serveur, pas de base de données, pas de compte : c'est une page web qui tourne entièrement dans votre navigateur, et quand vous le branchez à Trello, votre navigateur parle directement à Trello. Le détail est dans la [politique de confidentialité](https://www.lilian-barty.fr/quadratt/confidentialite.html).

Et il ne décide pas à votre place. Il pose les questions dans le bon ordre ; les réponses restent les vôtres (c'est bien là tout le problème, je sais).

Si vous cherchez un vrai gestionnaire de projet, avec échéances, équipes et relances, ce n'est pas ça. Quadratt sert à une seule chose : sortir de la paralysie devant une liste trop longue.

## Ce dépôt

Le code est ici pour être lu. La version en ligne est la référence : ce dépôt est mis à jour à partir d'elle.

- `index.html` : l'outil entier, en un seul fichier
- `confidentialite.html`, `mentions-legales.html` : les pages légales
- `verifier.py` : les contrôles lancés avant chaque mise en ligne

Un bug, une idée ? Ouvrez une issue, ou écrivez à lilianchristophe.pro@gmail.com.

## Qui l'a fait

Lilian Barty-Christophe, consultant freelance en IA à Paris ([lilian-barty.fr](https://www.lilian-barty.fr/)). Je l'ai construit pour trier mon propre tableau Trello, qui débordait.

## Licence

Code visible, tous droits réservés. Vous pouvez le lire et vous en inspirer, pas le republier tel quel. Pour un autre usage, écrivez-moi.

## In English

Quadratt sorts your to-dos into four boxes (urgent? high impact?) so you know what to tackle first. It works on a Trello board, writing the result as labels, or without any account in a local notebook. Everything runs in your browser: no server, no data collected. Try it at [lilian-barty.fr/quadratt](https://www.lilian-barty.fr/quadratt/). Source visible, all rights reserved.
