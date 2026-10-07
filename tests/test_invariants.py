"""Invariants annoncés dans le README : pas de regard vers le futur, frais déduits,
comparaison avec l'achat simple, paper trading uniquement (GET seulement)."""

import numpy as np
import pandas as pd
import pytest

import alpaca_client
import backtest


def _serie(n=120, seed=7):
    rng = np.random.default_rng(seed)
    cloture = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame({"cloture": cloture, "haut": cloture * 1.005}, index=idx)


def test_la_position_du_jour_J_vient_du_signal_du_jour_J_moins_1():
    df = _serie()
    signal = pd.Series(1, index=df.index)
    d = backtest.executer(df, signal)["courbe"]
    assert d["position"].iloc[0] == 0
    assert (d["position"].iloc[1:] == 1).all()


@pytest.mark.parametrize("strategie", ["Croisement de moyennes mobiles", "Franchissement d'un plus haut"])
def test_un_signal_ne_depend_pas_des_cours_futurs(strategie):
    df = _serie()
    f = backtest.STRATEGIES[strategie]
    complet = f(df)
    for k in (60, 90):
        assert complet.iloc[:k].equals(f(df.iloc[:k]))


def test_changer_le_dernier_cours_ne_change_pas_le_capital_des_jours_precedents():
    df = _serie()
    modifie = df.copy()
    modifie.iloc[-1, modifie.columns.get_loc("cloture")] *= 1.5
    signal = backtest.moyennes_mobiles(df)
    a = backtest.executer(df, signal)["courbe"]["capital"]
    b = backtest.executer(modifie, signal)["courbe"]["capital"]
    assert a.iloc[:-1].equals(b.iloc[:-1])


def test_les_frais_sont_deduits_a_chaque_changement_de_position():
    df = _serie()
    signal = backtest.moyennes_mobiles(df)
    sans = backtest.executer(df, signal, frais_pct=0.0)["resultats"]
    avec = backtest.executer(df, signal, frais_pct=0.5)["resultats"]
    assert avec["nb_ordres"] == sans["nb_ordres"] > 0
    assert avec["capital_final"] < sans["capital_final"]


def test_la_comparaison_avec_l_achat_simple_est_toujours_fournie_et_exacte():
    df = _serie()
    res = backtest.executer(df, backtest.toujours_investi(df))["resultats"]
    attendu = (df["cloture"].iloc[-1] / df["cloture"].iloc[0] - 1) * 100
    assert res["gain_achat_simple_pct"] == pytest.approx(attendu)
    assert "ecart_vs_achat_simple_pct" in res


def test_l_url_de_trading_est_le_bac_a_sable():
    assert alpaca_client.BASE_TRADING == "https://paper-api.alpaca.markets"
    assert "paper" in alpaca_client.BASE_TRADING


def test_aucun_appel_reseau_n_est_autre_chose_qu_un_get(monkeypatch):
    monkeypatch.setattr(alpaca_client, "CLE", "k")
    monkeypatch.setattr(alpaca_client, "SECRET", "s")
    vus = []

    class Rep:
        status_code = 200

        def json(self):
            return {}

    def get(url, **kw):
        vus.append(url)
        return Rep()

    def interdit(*a, **kw):
        raise AssertionError("méthode non-GET appelée")

    monkeypatch.setattr(alpaca_client.requests, "get", get)
    for nom in ("post", "put", "patch", "delete"):
        monkeypatch.setattr(alpaca_client.requests, nom, interdit)
    alpaca_client.compte()
    alpaca_client.positions()
    assert vus and all(u.startswith("https://paper-api.alpaca.markets/") for u in vus)


def test_sans_cles_le_client_ne_contacte_rien(monkeypatch):
    monkeypatch.setattr(alpaca_client, "CLE", "")
    monkeypatch.setattr(alpaca_client, "SECRET", "")
    monkeypatch.setattr(alpaca_client.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("réseau")))
    assert not alpaca_client.compte()
