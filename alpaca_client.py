"""Accès à Alpaca — paper trading uniquement.

Deux règles tenues par ce fichier :

1. Aucune clé n'est écrite en dur. Elles viennent de l'environnement.
2. L'URL de base est verrouillée sur le bac à sable (paper-api). Aucun ordre
   réel ne peut partir d'ici, même par erreur de configuration.

Comme pour le cockpit : on ne renvoie jamais un chiffre inventé. Si la source
est indisponible, on renvoie Indispo(raison) que l'interface affiche telle quelle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# Verrouillage : bac à sable, jamais l'API de production.
BASE_TRADING = "https://paper-api.alpaca.markets"
BASE_DONNEES = "https://data.alpaca.markets"

CLE = os.environ.get("ALPACA_KEY_ID", "")
SECRET = os.environ.get("ALPACA_SECRET_KEY", "")


@dataclass
class Indispo:
    raison: str

    def __bool__(self) -> bool:
        return False


def _entetes() -> dict:
    return {
        "APCA-API-KEY-ID": CLE,
        "APCA-API-SECRET-KEY": SECRET,
        "accept": "application/json",
    }


def cles_presentes() -> bool:
    return bool(CLE and SECRET)


def _appel(base: str, chemin: str, params: dict | None = None):
    if not cles_presentes():
        return Indispo(
            "clés absentes — définis ALPACA_KEY_ID et ALPACA_SECRET_KEY "
            "(clés de paper trading, jamais des clés de compte réel)"
        )
    try:
        rep = requests.get(
            f"{base}{chemin}", headers=_entetes(), params=params or {}, timeout=20
        )
    except requests.RequestException as exc:
        return Indispo(f"Alpaca injoignable : {exc}")

    if rep.status_code == 401:
        return Indispo("clés refusées (401) — vérifie que ce sont bien des clés *paper*")
    if rep.status_code == 403:
        return Indispo("accès refusé (403) — ton offre de données ne couvre pas cette requête")
    if rep.status_code == 429:
        return Indispo("trop de requêtes (429) — attends une minute avant de réessayer")
    if rep.status_code != 200:
        return Indispo(f"Alpaca a répondu {rep.status_code}")
    return rep.json()


# ---------------------------------------------------------------------------
# Compte
# ---------------------------------------------------------------------------


def compte():
    """État du portefeuille fictif."""
    data = _appel(BASE_TRADING, "/v2/account")
    if isinstance(data, Indispo):
        return data
    return {
        "statut": data.get("status"),
        "devise": data.get("currency"),
        "liquidites": float(data.get("cash", 0)),
        "valeur_portefeuille": float(data.get("portfolio_value", 0)),
        "pouvoir_achat": float(data.get("buying_power", 0)),
        "compte_bloque": data.get("trading_blocked"),
    }


def positions():
    data = _appel(BASE_TRADING, "/v2/positions")
    if isinstance(data, Indispo):
        return data
    if not data:
        return []
    return [
        {
            "titre": p.get("symbol"),
            "quantite": float(p.get("qty", 0)),
            "prix_moyen": float(p.get("avg_entry_price", 0)),
            "valeur": float(p.get("market_value", 0)),
            "gain_latent": float(p.get("unrealized_pl", 0)),
            "gain_latent_pct": float(p.get("unrealized_plpc", 0)) * 100,
        }
        for p in data
    ]


# ---------------------------------------------------------------------------
# Données de marché
# ---------------------------------------------------------------------------


def historique(titre: str, jours: int = 365, granularite: str = "1Day"):
    """Cours historiques. Renvoie un DataFrame indexé par date."""
    debut = (datetime.now(timezone.utc) - timedelta(days=jours)).date().isoformat()
    data = _appel(
        BASE_DONNEES,
        f"/v2/stocks/{titre.upper()}/bars",
        {"timeframe": granularite, "start": debut, "limit": 10000, "feed": "iex"},
    )
    if isinstance(data, Indispo):
        return data

    barres = data.get("bars") or []
    if not barres:
        return Indispo(
            f"aucune donnée pour « {titre.upper()} » — vérifie le symbole "
            "(ce sont des titres américains : AAPL, MSFT, TSLA…)"
        )

    df = pd.DataFrame(barres)
    df["date"] = pd.to_datetime(df["t"]).dt.tz_convert(None)
    df = df.rename(
        columns={"o": "ouverture", "h": "haut", "l": "bas", "c": "cloture", "v": "volume"}
    )
    return df[["date", "ouverture", "haut", "bas", "cloture", "volume"]].set_index("date")


def rechercher_titre(fragment: str):
    """Liste des titres négociables dont le nom ou le symbole correspond."""
    data = _appel(BASE_TRADING, "/v2/assets", {"status": "active", "asset_class": "us_equity"})
    if isinstance(data, Indispo):
        return data
    f = fragment.strip().lower()
    if not f:
        return []
    trouves = [
        {"symbole": a["symbol"], "nom": a.get("name", ""), "bourse": a.get("exchange", "")}
        for a in data
        if a.get("tradable") and (f in a["symbol"].lower() or f in (a.get("name") or "").lower())
    ]
    return trouves[:40]
