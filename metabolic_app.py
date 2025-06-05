import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ===========================
# 🔐 Authentification
# ===========================
st.set_page_config(page_title="Suivi Métabolique", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("🔐 Mot de passe", type="password")
    if password and password == st.secrets["APP_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("Mot de passe incorrect.")
    st.stop()


# ===========================
# 📥 Chargement des données (local par défaut)
# ===========================
default_path = "data/metabo_data.csv"
df = pd.read_csv(default_path)
df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Heure"], format="%d/%m/%Y %H:%M")

# =============================================================================================
# ================================ ⚙️ Fonctions principales ===================================
# =============================================================================================

# ===========================
# 🧮 Préparation unique avec fonction
# ===========================

def prepare_df_plot(df, unit_glucose, unit_ketone, gki_mode, debug=False):
    df_plot = df.copy()

    # Affichage indépendant
    df_plot["Glycémie_affichée"] = (
        df_plot["Glycémie"] / 18.01559 if unit_glucose == "mmol/L" else df_plot["Glycémie"]
    )
    df_plot["Cétonémie_affichée"] = df_plot["Cétonémie"]  # conversion future si besoin

    # Calcul GKI
    if gki_mode == "Full mmol":
        gly_mmol = (
            df_plot["Glycémie"] / 18.01559 if unit_glucose == "mg/dL" else df_plot["Glycémie"]
        )
    else:  # standard glycémie en mg/dL, puis converti en mmol/L
        gly_mmol = (
            df_plot["Glycémie"] if unit_glucose == "mg/dL" else df_plot["Glycémie"] * 18.01559
        )
        gly_mmol = gly_mmol / 18.01559

    df_plot["GKI"] = gly_mmol / df_plot["Cétonémie"]

    if debug:
        print(df_plot[["Glycémie", "Cétonémie", "GKI"]])

    return df_plot


# ===========================================================================================
# ##################### ✅ Auto-vérification des conversions (interne) ######################
# ===========================================================================================

# 🧪 Test de la conversion glucose mg/dL → mmol/L → mg/dL
def test_glucose_conversion():
    mg_dl = 90
    mmol_l = mg_dl / 18.01559
    reconverted = mmol_l * 18.01559

    assert abs(reconverted - mg_dl) < 0.1, "Conversion glucose mg/dL → mmol/L → mg/dL incorrecte"

# 🧪 Test du GKI
def test_gki_calculation():
    test_data = pd.DataFrame({
        "Glycémie": [90, 108],  # mg/dL
        "Cétonémie": [1.5, 2.0],
        "Date": ["01/01/2024", "02/01/2024"],
        "Heure": ["08:00", "08:00"]
    })
    test_data["Datetime"] = pd.to_datetime(test_data["Date"] + " " + test_data["Heure"], format="%d/%m/%Y %H:%M")

    df1 = prepare_df_plot(test_data, "mg/dL", "mmol/L", "Standard (mg/dL/mmol)", debug=True)
    df2 = prepare_df_plot(test_data, "mg/dL", "mmol/L", "Full mmol", debug=True)

    # Cas 1 : Standard (mg/dL → mmol/L)
    expected1 = [(90/18.01559)/1.5, (108/18.01559)/2.0]
    assert all(abs(a - b) < 1e-6 for a, b in zip(df1["GKI"], expected1)), "Erreur GKI standard"

    # Cas 2 : Full mmol
    expected2 = [(90/18.01559)/1.5, (108/18.01559)/2.0]
    assert all(abs(a - b) < 1e-6 for a, b in zip(df2["GKI"], expected2)), "Erreur GKI full mmol"

def test_prepare_df_plot():
    test_df = pd.DataFrame({
        "Date": ["01/01/2024"],
        "Heure": ["12:00"],
        "Glycémie": [90],
        "Cétonémie": [1.5]
    })
    test_df["Datetime"] = pd.to_datetime(test_df["Date"] + " " + test_df["Heure"], format="%d/%m/%Y %H:%M")
    
    out = prepare_df_plot(test_df, "mg/dL", "mmol/L", "Standard (mg/dL/mmol)")
    expected = (90 / 18.01559) / 1.5  # conversion en mmol/L puis division
    assert "GKI" in out.columns, "GKI non calculé"
    assert abs(out["GKI"].iloc[0] - expected) < 1e-6, "GKI incorrect"


try:
    test_glucose_conversion()
    test_gki_calculation()
    test_prepare_df_plot()
except AssertionError as e:
    print(f"[❌ TEST ÉCHOUÉ] {e}")
else:
    print("[✅ TESTS UNITAIRES PASSÉS]")



# =============================================================================================
# ================================ ⚙️ Interface utilisateur ===================================
# =============================================================================================

st.title("📈 Suivi métabolique")

st.markdown("---")  # ligne de séparation

# ===========================
# ⚙️ Paramètres d’analyse
# ===========================

st.markdown("### ⚙️ Paramètres d’analyse")

colA, colB, colC = st.columns(3)
with colA:
    unit_glucose = st.selectbox("🩸 Unité de glycémie", ["mg/dL", "mmol/L"], index=1)
with colB:
    unit_ketone = st.selectbox("💧 Unité de cétonémie", ["mmol/L"], index=0)
with colC:
    gki_mode = st.selectbox("🧮 Mode de calcul GKI", ["Standard (mg/dL/mmol)", "Full mmol"], index=1)

df_plot = prepare_df_plot(df, unit_glucose, unit_ketone, gki_mode)

st.markdown("---")  # ligne de séparation
# =============================================================================================
# ======================================= 📊 Graphe intéractif ================================
# =============================================================================================

df_long = df_plot.melt(
    id_vars="Datetime",
    value_vars=["Glycémie", "Cétonémie", "GKI"],
    var_name="Paramètre",
    value_name="Valeur"
)

fig = px.line(
    df_long,
    x="Datetime",
    y="Valeur",
    color="Paramètre",
    markers=True,
    title="Évolution : Glycémie / Cétonémie / GKI",
    labels={
        "Valeur": "Valeur",
        "Paramètre": f"Paramètre ({unit_glucose}, {unit_ketone}, GKI mode: {gki_mode})",
        "Datetime": ""
    },
    color_discrete_map={
        "Glycémie": "#e74c3c",   # rouge
        "Cétonémie": "#2980b9",  # bleu
        "GKI": "#27ae60"         # vert
    }
)

fig.update_layout(
    xaxis_title="Temps",
    yaxis_title="Valeur",
    hovermode="x unified",
    legend_title="Paramètre",
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(step="all", label="Tout"),
                dict(count=30, label="30j", step="day", stepmode="backward"),
                dict(count=7, label="7j", step="day", stepmode="backward"),
                dict(count=2, label="48h", step="day", stepmode="backward"),
                dict(count=1, label="24h", step="day", stepmode="backward"),
            ]),
            bgcolor="rgba(50,50,50,0.5)",
            activecolor="rgba(200,200,200,0.9)",
            font=dict(size=12, color="white")
        ),
        rangeslider=dict(visible=True),
        type="date"
    )
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")  # ligne de séparation

# =============================================================================================
# ======================================= 🧾 Statistiques ===================================
# =============================================================================================
st.subheader("📊 Statistiques clés")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Nb Mesures", len(df_plot))
col2.metric(f"🩸 Glycémie (moy)", f"{df_plot['Glycémie'].mean():.1f} {unit_glucose}")
col3.metric("💧 Cétonémie (moy)", f"{df_plot['Cétonémie'].mean():.2f} {unit_ketone}")
col4.metric("GKI (moy)", f"{df_plot['GKI'].mean():.2f}")