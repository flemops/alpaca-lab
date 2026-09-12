"""Laboratoire Alpaca — simulation uniquement.

Interface volontairement dépouillée : trois onglets, aucun jargon non expliqué,
aucune recommandation. L'outil montre ce qui se serait passé ; il ne dit jamais
quoi acheter.
"""

import pandas as pd
import streamlit as st

import alpaca_client as ac
import backtest as bt

st.set_page_config(page_title="Laboratoire Alpaca", page_icon="🧪", layout="wide")

# --- Bandeau permanent : on ne doit jamais croire qu'il s'agit d'argent réel ---
st.markdown(
    """
    <div style="background:#1f3a2e;border-left:4px solid #35c46b;padding:.7rem 1rem;
                border-radius:6px;margin-bottom:1.2rem;font-size:.92rem">
    <strong>Simulation.</strong> Aucun argent réel n'est engagé et aucun ordre n'est passé.
    Cet outil sert à comprendre et à tester, pas à investir.
    </div>
    """,
    unsafe_allow_html=True,
)


def afficher_si_indispo(valeur) -> bool:
    if isinstance(valeur, ac.Indispo):
        st.warning(f"Indisponible — {valeur.raison}")
        return True
    return False


onglet_decouverte, onglet_test, onglet_compte = st.tabs(
    ["Explorer un titre", "Tester une stratégie", "Mon portefeuille fictif"]
)

# ---------------------------------------------------------------------------
# 1. Explorer
# ---------------------------------------------------------------------------
with onglet_decouverte:
    st.subheader("Regarder l'évolution d'une action")
    st.caption(
        "Tape le symbole d'une entreprise américaine — AAPL pour Apple, "
        "MSFT pour Microsoft, TSLA pour Tesla."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        titre = st.text_input("Symbole", value="AAPL", key="titre_explo").strip().upper()
        periode = st.select_slider(
            "Période observée",
            options=[90, 180, 365, 730, 1825],
            value=365,
            format_func=lambda j: f"{j // 365} an(s)" if j >= 365 else f"{j} jours",
        )

    if titre:
        donnees = ac.historique(titre, jours=periode)
        if not afficher_si_indispo(donnees):
            dernier = float(donnees["cloture"].iloc[-1])
            premier = float(donnees["cloture"].iloc[0])
            variation = (dernier / premier - 1) * 100

            a, b, c = st.columns(3)
            a.metric("Dernier cours", f"{dernier:,.2f} $")
            b.metric("Sur la période", f"{variation:+.1f} %")
            c.metric("Séances", f"{len(donnees):,}")

            st.line_chart(donnees["cloture"], height=320)
            with st.expander("Voir les données brutes"):
                st.dataframe(donnees.tail(60), use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Tester une stratégie
# ---------------------------------------------------------------------------
with onglet_test:
    st.subheader("Et si j'avais appliqué cette règle ?")
    st.caption(
        "On rejoue le passé en appliquant une règle mécanique, puis on compare "
        "au fait d'avoir simplement acheté au début sans plus y toucher."
    )

    g, d = st.columns([1, 2])
    with g:
        titre_test = st.text_input("Symbole", value="AAPL", key="titre_test").strip().upper()
        nom_strategie = st.selectbox("Règle à tester", list(bt.STRATEGIES.keys()))
        annees = st.slider("Nombre d'années", 1, 5, 2)
        capital = st.number_input("Capital de départ ($)", 1000, 1_000_000, 10_000, step=1000)

        if nom_strategie == "Croisement de moyennes mobiles":
            courte = st.slider("Moyenne courte (jours)", 5, 50, 20)
            longue = st.slider("Moyenne longue (jours)", 20, 200, 50)
        elif nom_strategie == "Franchissement d'un plus haut":
            fenetre = st.slider("Fenêtre (jours)", 5, 100, 20)

        lancer = st.button("Lancer le test", type="primary", use_container_width=True)

    if lancer and titre_test:
        donnees = ac.historique(titre_test, jours=annees * 365)
        if not afficher_si_indispo(donnees):
            fn = bt.STRATEGIES[nom_strategie]
            if nom_strategie == "Croisement de moyennes mobiles":
                signal = fn(donnees, courte, longue)
            elif nom_strategie == "Franchissement d'un plus haut":
                signal = fn(donnees, fenetre)
            else:
                signal = fn(donnees)

            sortie = bt.executer(donnees, signal, capital_depart=float(capital))
            r = sortie["resultats"]

            with d:
                ecart = r["ecart_vs_achat_simple_pct"]
                if ecart > 0:
                    st.success(
                        f"Sur cette période, la règle aurait fait **{ecart:+.1f} points** "
                        "de mieux que d'acheter et ne rien faire."
                    )
                else:
                    st.error(
                        f"Sur cette période, la règle aurait fait **{ecart:+.1f} points** "
                        "de moins que d'acheter et ne rien faire."
                    )

                st.line_chart(
                    sortie["courbe"][["capital", "capital_achat_simple"]].rename(
                        columns={
                            "capital": "Avec la règle",
                            "capital_achat_simple": "Acheter et ne rien faire",
                        }
                    ),
                    height=300,
                )

            st.divider()
            m = st.columns(4)
            m[0].metric("Capital final", f"{r['capital_final']:,.0f} $",
                        f"{r['gain_total_pct']:+.1f} %")
            m[1].metric("Par an", f"{r['rendement_annuel_pct']:+.1f} %",
                        help="Rendement moyen ramené à une année.")
            m[2].metric("Pire chute", f"{r['pire_perte_pct']:.1f} %",
                        help="La plus forte baisse subie avant de remonter. "
                             "C'est ce qu'il aurait fallu supporter sans vendre.")
            m[3].metric("Rendement / risque", f"{r['rendement_sur_risque']:.2f}",
                        help="Au-dessus de 1, le gain justifie les secousses. "
                             "En dessous de 0,5, le jeu n'en vaut pas la chandelle.")

            n = st.columns(3)
            n[0].metric("Ordres passés", r["nb_ordres"])
            n[1].metric("Temps investi", f"{r['temps_investi_pct']:.0f} %",
                        help="Part du temps où l'argent était réellement placé.")
            n[2].metric("Durée testée", f"{r['duree_annees']:.1f} ans")

            st.info(
                "**À lire avant de conclure.** Un bon résultat sur le passé ne prédit "
                "rien : en essayant assez de réglages, on finit toujours par en trouver "
                "un qui aurait marché. Ce test inclut les frais et n'utilise jamais une "
                "information que tu n'aurais pas eue le jour même — mais il reste une "
                "simulation, pas une prévision."
            )

# ---------------------------------------------------------------------------
# 3. Portefeuille fictif
# ---------------------------------------------------------------------------
with onglet_compte:
    st.subheader("Le portefeuille de simulation")

    if not ac.cles_presentes():
        st.warning(
            "Aucune clé configurée. Crée un compte gratuit sur alpaca.markets, "
            "génère des clés **paper trading**, puis place-les dans les variables "
            "d'environnement `ALPACA_KEY_ID` et `ALPACA_SECRET_KEY`. "
            "N'utilise jamais des clés de compte réel avec cet outil."
        )
    else:
        infos = ac.compte()
        if not afficher_si_indispo(infos):
            a, b, c = st.columns(3)
            a.metric("Valeur totale", f"{infos['valeur_portefeuille']:,.0f} $")
            b.metric("Liquidités", f"{infos['liquidites']:,.0f} $")
            c.metric("Capacité d'achat", f"{infos['pouvoir_achat']:,.0f} $")

            lignes = ac.positions()
            if not afficher_si_indispo(lignes):
                if lignes:
                    st.dataframe(pd.DataFrame(lignes), use_container_width=True)
                else:
                    st.caption("Aucune position ouverte.")
