# Laboratoire Alpaca

Outil de simulation boursière. **Aucun argent réel, aucun ordre passé** — l'URL de
l'API est verrouillée dans le code sur le bac à sable (`paper-api.alpaca.markets`),
un ordre réel ne peut donc pas partir d'ici, même par erreur de configuration.

## Installation

```bash
cd alpaca-lab
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Clés

1. Créer un compte gratuit sur alpaca.markets (une adresse e-mail suffit, aucune
   pièce d'identité, ouvert depuis la France).
2. Générer des clés **Paper Trading** — jamais des clés de compte réel.
3. Les placer en variables d'environnement :

```powershell
$env:ALPACA_KEY_ID     = "..."
$env:ALPACA_SECRET_KEY = "..."
```

Sur la VM, passer par un `EnvironmentFile` systemd. Ne jamais écrire les clés
dans un fichier du dépôt.

## Lancer

```bash
streamlit run app.py
```

## Ce que fait l'outil

| Onglet | Rôle |
|---|---|
| Explorer un titre | courbe et données brutes d'une action américaine |
| Tester une stratégie | rejoue une règle mécanique sur le passé et la compare à « acheter et ne rien faire » |
| Portefeuille fictif | état du compte de simulation et positions ouvertes |

## Ce qu'il ne fait pas, volontairement

- Il ne passe aucun ordre, même fictif : c'est un outil d'observation.
- Il ne recommande jamais un titre ni un moment d'achat.
- Il n'affiche aucun chiffre qu'il n'a pas lu à la source. Si une donnée manque,
  il écrit pourquoi.

## Trois précautions intégrées au calcul

1. **Aucun regard vers le futur** : un signal calculé sur la clôture du jour J
   n'est appliqué qu'à partir de J+1. Sans cette règle, tout backtest paraît
   brillant — et ne vaut rien.
2. **Frais déduits** à chaque passage d'ordre (0,05 % par défaut).
3. **Comparaison imposée** avec l'achat simple. C'est la seule référence
   honnête : une stratégie qui gagne 8 % pendant que le marché en gagne 20 %
   a détruit de la valeur.

## Limite qu'aucun outil ne peut lever

Un bon résultat passé ne prédit rien. En testant assez de réglages, on trouve
toujours une combinaison qui aurait fonctionné — c'est du hasard habillé en
méthode. Cet outil sert à comprendre des mécanismes, pas à décider d'un placement.

*Ni cet outil ni son auteur ne fournissent de conseil en investissement.*
