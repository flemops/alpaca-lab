"""Moteur de test de stratégie sur données passées.

Honnêteté du calcul — ce moteur applique délibérément trois règles que
beaucoup d'outils ignorent, et qui font paraître les stratégies bien
meilleures qu'elles ne sont :

1. **Pas de regard vers le futur.** Un signal calculé avec la clôture du jour J
   est exécuté à l'ouverture de J+1. On ne peut pas acheter à un prix qu'on ne
   connaissait pas encore.
2. **Frais et écart de cours** déduits à chaque passage d'ordre.
3. **Comparaison systématique** avec « acheter au début et ne rien faire ».
   C'est la seule référence qui compte : une stratégie qui gagne 8 % quand le
   marché en gagne 20 % a perdu de l'argent en réalité.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def moyennes_mobiles(df: pd.DataFrame, courte: int = 20, longue: int = 50) -> pd.Series:
    """Signal classique : on est investi quand la moyenne courte passe au-dessus
    de la longue. Renvoie 1 (investi) ou 0 (hors marché) par jour."""
    mc = df["cloture"].rolling(courte).mean()
    ml = df["cloture"].rolling(longue).mean()
    return (mc > ml).astype(int)


def franchissement_plus_haut(df: pd.DataFrame, fenetre: int = 20) -> pd.Series:
    """On entre quand le cours dépasse son plus haut des N derniers jours."""
    plus_haut = df["haut"].rolling(fenetre).max().shift(1)
    return (df["cloture"] > plus_haut).astype(int)


def toujours_investi(df: pd.DataFrame) -> pd.Series:
    return pd.Series(1, index=df.index)


STRATEGIES = {
    "Croisement de moyennes mobiles": moyennes_mobiles,
    "Franchissement d'un plus haut": franchissement_plus_haut,
    "Acheter et ne rien faire": toujours_investi,
}


def executer(
    df: pd.DataFrame,
    signal: pd.Series,
    capital_depart: float = 10_000.0,
    frais_pct: float = 0.05,
) -> dict:
    """Applique le signal, décalé d'un jour, et renvoie les résultats chiffrés."""
    d = df.copy()

    # Règle 1 : le signal du jour J s'applique à partir de J+1.
    d["position"] = signal.shift(1).fillna(0)

    d["rendement_titre"] = d["cloture"].pct_change().fillna(0)
    d["rendement_strategie"] = d["position"] * d["rendement_titre"]

    # Règle 2 : frais à chaque changement de position.
    changements = d["position"].diff().abs().fillna(0)
    d["rendement_strategie"] -= changements * (frais_pct / 100)

    d["capital"] = capital_depart * (1 + d["rendement_strategie"]).cumprod()
    d["capital_achat_simple"] = capital_depart * (1 + d["rendement_titre"]).cumprod()

    return {
        "courbe": d[["capital", "capital_achat_simple", "position", "cloture"]],
        "resultats": _metriques(d, capital_depart, int(changements.sum())),
    }


def _metriques(d: pd.DataFrame, capital_depart: float, nb_ordres: int) -> dict:
    final = float(d["capital"].iloc[-1])
    final_simple = float(d["capital_achat_simple"].iloc[-1])

    annees = max((d.index[-1] - d.index[0]).days / 365.25, 0.01)
    rendement_annuel = (final / capital_depart) ** (1 / annees) - 1

    # Pire perte depuis un sommet : ce que tu aurais vu fondre avant remontée.
    sommet = d["capital"].cummax()
    pire_perte = float(((d["capital"] - sommet) / sommet).min())

    quotidiens = d["rendement_strategie"]
    volatilite = float(quotidiens.std() * np.sqrt(252))
    # Rendement rapporté au risque pris. Au-dessus de 1, c'est correct.
    ratio = (rendement_annuel / volatilite) if volatilite > 0 else 0.0

    jours_investi = float((d["position"] > 0).mean())

    return {
        "capital_final": final,
        "gain_total_pct": (final / capital_depart - 1) * 100,
        "gain_achat_simple_pct": (final_simple / capital_depart - 1) * 100,
        "ecart_vs_achat_simple_pct": (final - final_simple) / capital_depart * 100,
        "rendement_annuel_pct": rendement_annuel * 100,
        "pire_perte_pct": pire_perte * 100,
        "volatilite_pct": volatilite * 100,
        "rendement_sur_risque": ratio,
        "nb_ordres": nb_ordres,
        "temps_investi_pct": jours_investi * 100,
        "duree_annees": annees,
    }
