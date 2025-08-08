import streamlit as st
import pandas as pd

st.set_page_config(page_title="Microcap Viewer", layout="wide")

# === 1. Choix du dataset ===
dataset_choice = st.sidebar.radio(
    "Dataset",
    [
        "Univers (micro_caps_extended)",
        "Potentiels (extended_to_potential)",
        "Analyses DS (potential_to_pepite)",
    ],
    index=0,
)


@st.cache_data
def load_universe():
    df = pd.read_csv(
        "enhanced_system/data/micro_caps_extended.csv",
        quotechar='"',
        escapechar='\\',
        encoding='utf-8',
    )
    expected_columns = [
        "Ticker",
        "Name",
        "Market Cap",
        "Price",
        "Sector",
        "Market",
        "Volume",
    ]
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes: {missing}")
        st.write("Colonnes disponibles:", df.columns.tolist())
        return pd.DataFrame()
    return df.dropna(subset=["Market Cap", "Price", "Volume"]) 


@st.cache_data
def load_potentials():
    df = pd.read_csv(
        "enhanced_system/data/extended_to_potential.csv",
        encoding='utf-8',
    )
    # Harmoniser quelques noms pour réutiliser une partie des filtres
    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})
    if "Exchange" in df.columns and "Market" not in df.columns:
        df = df.rename(columns={"Exchange": "Market"})
    if "CompanyName" in df.columns and "Name" not in df.columns:
        df = df.rename(columns={"CompanyName": "Name"})
    # Colonnes minimales
    expected_columns = ["Ticker", "Market Cap", "Price", "Volume", "Sector", "Market", "ScorePotential"]
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        st.warning(f"ℹ️ Dataset potentiels: colonnes manquantes non bloquantes: {missing}")
    return df


@st.cache_data
def load_ds_analysis():
    df = pd.read_csv(
        "enhanced_system/data/potential_to_pepite.csv",
        encoding='utf-8',
    )
    # Harmonisations légères
    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})
    if "Exchange" in df.columns and "Market" not in df.columns:
        df = df.rename(columns={"Exchange": "Market"})
    if "CompanyName" in df.columns and "Name" not in df.columns:
        df = df.rename(columns={"CompanyName": "Name"})
    return df


if dataset_choice.startswith("Univers"):
    df = load_universe()
elif dataset_choice.startswith("Potentiels"):
    df = load_potentials()
else:
    df = load_ds_analysis()


st.title("📊 Microcaps Viewer – Analyse et Scoring interactif")

# === 2. Sidebar : Filtres ===
st.sidebar.header("🔎 Filtres")

if "Market" in df.columns:
    markets = st.sidebar.multiselect(
        "Marchés",
        options=sorted(df["Market"].dropna().unique()),
        default=sorted(df["Market"].dropna().unique()),
    )
else:
    markets = []

if "Sector" in df.columns:
    sectors = st.sidebar.multiselect(
        "Secteurs",
        options=sorted(df["Sector"].dropna().unique()),
        default=sorted(df["Sector"].dropna().unique()),
    )
else:
    sectors = []

# === Filtres numériques avec champs de saisie ===
st.sidebar.markdown("### 📊 Filtres numériques")

# Utilise une seule colonne sur toute la largeur
# Market Cap
use_cap_filter = st.sidebar.checkbox(
    "Filtrer par Market Cap –💡 Min-Max en M$",
    value=True,
    help="💡 Min-Max exprimé en millions de dollars (M$)"
)

if use_cap_filter:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        cap_min = st.number_input("Min (M$)", min_value=0, max_value=100_000, value=74, label_visibility="collapsed")
    with col2:
        cap_max = st.number_input("Max (M$)", min_value=0, max_value=100_000, value=75, label_visibility="collapsed")
    cap_range = (cap_min * 1_000_000, cap_max * 1_000_000)
else:
    cap_range = (0, float('inf'))

# Prix
use_price_filter = st.sidebar.checkbox(
    "Filtrer par Prix –💡 Min-Max en $",
    value=True,
    help="💡 Min-Max exprimé en dollars ($)"
)

if use_price_filter:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        price_min = st.number_input("Min $", min_value=0.0, max_value=1000.0, value=1.0, step=0.1, label_visibility="collapsed")
    with col2:
        price_max = st.number_input("Max $", min_value=0.0, max_value=1000.0, value=30.0, step=0.1, label_visibility="collapsed")
    price_range = (price_min, price_max)
else:
    price_range = (0.0, float('inf'))

# Volume
use_volume_filter = st.sidebar.checkbox(
    "Filtrer par Volume –💡 Min-Max en nombre d'actions échangées",
    value=True,
    help="💡 Min-Max exprimé en nombre d'actions échangées"
)

if use_volume_filter:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        volume_min = st.number_input("Min Vol", min_value=0, max_value=100_000_000, value=1000, step=1000, label_visibility="collapsed")
    with col2:
        volume_max = st.number_input("Max Vol", min_value=0, max_value=100_000_000, value=1000000, step=1000, label_visibility="collapsed")
    volume_range = (volume_min, volume_max)
else:
    volume_range = (0, float('inf'))

short_ratio_range = (0.0, 1.0)
if dataset_choice.startswith("Univers") and "shortRatio" in df.columns:
    short_ratio_max = df["shortRatio"].max(skipna=True)
    if pd.notna(short_ratio_max):
        short_ratio_range = st.sidebar.slider(
            "Short Ratio", 0.0, float(short_ratio_max), (0.0, float(short_ratio_max))
        )

# === 3. Sidebar : Scoring ===
st.sidebar.header("📈 Poids du Scoring")

if dataset_choice.startswith("Univers"):
    w_price = st.sidebar.slider(
        "📉 Poids Prix (1/Prix)", 0.0, 10.0, 2.0,
        help="Plus le prix est bas, plus la contribution est élevée (1/Prix)."
    )
    w_volume = st.sidebar.slider(
        "🔊 Poids Volume", 0.0, 10.0, 1.0,
        help="Volume (en millions) accentue la liquidité."
    )
    w_cap = st.sidebar.slider(
        "🏢 Poids Market Cap (inverse)", 0.0, 5.0, 0.5,
        help="Favorise les capitalisations plus petites (1/Market Cap)."
    )
    w_short = st.sidebar.slider(
        "⚠️ Poids Short Ratio", 0.0, 10.0, 3.0,
        help="Accentue les valeurs avec un short ratio élevé (potentiel squeeze)."
    ) if "shortRatio" in df.columns else 0
else:
    use_composite = st.sidebar.checkbox(
        "Activer Score composite (Potentiels)", value=True,
        help="Combine ScorePotential (Étape 1) avec des facteurs simples (Prix, Volume, MC)."
    )
    w_sp = st.sidebar.slider(
        "⭐ Poids ScorePotential", 0.0, 3.0, 1.0,
        help="Importance du ScorePotential calculé par Étape 1."
    )
    w_price = st.sidebar.slider(
        "📉 Poids Prix (1/Prix)", 0.0, 5.0, 0.5,
        help="Plus le prix est bas, plus la contribution est élevée (1/Prix)."
    )
    w_volume = st.sidebar.slider(
        "🔊 Poids Volume", 0.0, 5.0, 0.5,
        help="Volume (en millions) accentue la liquidité."
    )
    w_cap = st.sidebar.slider(
        "🏢 Poids Market Cap (inverse)", 0.0, 3.0, 0.2,
        help="Favorise les capitalisations plus petites (1/Market Cap)."
    )

filtered = df.copy()
if "Market" in filtered.columns and markets:
    filtered = filtered[filtered["Market"].isin(markets)]
if "Sector" in filtered.columns and sectors:
    filtered = filtered[filtered["Sector"].isin(sectors)]
if "Market Cap" in filtered.columns:
    filtered = filtered[filtered["Market Cap"].between(*cap_range)]
if "Price" in filtered.columns:
    filtered = filtered[filtered["Price"].between(*price_range)]
if "Volume" in filtered.columns:
    filtered = filtered[filtered["Volume"].between(*volume_range)]
if dataset_choice.startswith("Univers") and "shortRatio" in filtered.columns:
    filtered = filtered[filtered["shortRatio"].between(*short_ratio_range)]

if dataset_choice.startswith("Univers"):
    # === 5. Calcul du Score ===
    filtered["Score"] = (
        w_price / filtered["Price"].replace(0, 1) +
        w_volume * (filtered["Volume"] / 1_000_000) +
        w_cap / filtered["Market Cap"].replace(0, 1)
    )
    if "shortRatio" in df.columns:
        filtered["Score"] += w_short * filtered["shortRatio"].fillna(0)
    filtered["Score"] = filtered["Score"].fillna(0)
    filtered = filtered.sort_values("Score", ascending=False).reset_index(drop=True)
elif dataset_choice.startswith("Potentiels"):
    # Tri par ScorePotential si disponible
    if "ScorePotential" in filtered.columns:
        if "Market Cap" in filtered.columns and "Price" in filtered.columns and "Volume" in filtered.columns and use_composite:
            filtered["ScoreComposite"] = (
                w_sp * filtered["ScorePotential"].fillna(0) +
                w_price / filtered["Price"].replace(0, 1) +
                w_volume * (filtered["Volume"] / 1_000_000) +
                w_cap / filtered["Market Cap"].replace(0, 1)
            ).fillna(0)
            filtered = filtered.sort_values("ScoreComposite", ascending=False).reset_index(drop=True)
        else:
            filtered = filtered.sort_values("ScorePotential", ascending=False).reset_index(drop=True)
else:
    # Vue Analyses DS: pas de recalcul, tri par confiance puis target/price
    if "DS_Confidence" in filtered.columns:
        # Si Price disponible, trier aussi par (DS_TargetPrice15d - Price)/Price
        if set(["DS_TargetPrice15d", "Price"]).issubset(filtered.columns):
            ret = (filtered["DS_TargetPrice15d"] - filtered["Price"]) / filtered["Price"].replace(0, 1)
            filtered = filtered.assign(_ret15=ret.fillna(0))
            filtered = filtered.sort_values(["DS_Confidence", "_ret15"], ascending=[False, False]).drop(columns=["_ret15"])\
                               .reset_index(drop=True)
        else:
            filtered = filtered.sort_values("DS_Confidence", ascending=False).reset_index(drop=True)

# === 6. Affichage tableau et détails ===
st.markdown(f"### 🎯 {len(filtered)} lignes affichées après filtrage")

with st.expander("ℹ️ Aide sur le scoring"):
    if dataset_choice.startswith("Univers"):
        st.markdown(
            """
            Score Univers = w_price × (1/Price) + w_volume × (Volume en millions) + w_cap × (1/Market Cap) [+ w_short × ShortRatio].
            - w_price: favorise les prix bas (évite la division par 0)
            - w_volume: met en avant la liquidité
            - w_cap: favorise les petites capitalisations
            - w_short: optionnel si la colonne est présente
            """
        )
    else:
        st.markdown(
            """
            Score Potentiels par défaut: tri par `ScorePotential` (calculé à l’Étape 1).
            Option “Score composite”: ScoreComposite = w_sp × ScorePotential + w_price × (1/Price) + w_volume × (Volume en millions) + w_cap × (1/Market Cap).
            """
        )

if dataset_choice.startswith("Univers"):
    selected_index = st.selectbox(
        "Sélectionner une ligne pour détails 👇",
        range(len(filtered)),
        format_func=lambda i: filtered.iloc[i]["Ticker"] if len(filtered) > 0 else "—",
    )
    cols = ["Ticker", "Name", "Market", "Sector", "Market Cap", "Price", "Volume"]
    if "shortRatio" in filtered.columns:
        cols += ["shortRatio"]
    cols += ["Score"]
    st.dataframe(filtered[cols], use_container_width=True)

    if len(filtered) > 0:
        sel = filtered.iloc[selected_index]
        st.sidebar.markdown("### 🧾 Détail de l'entreprise sélectionnée")
        st.sidebar.markdown(f"**Ticker :** `{sel['Ticker']}`")
        st.sidebar.markdown(f"**Nom :** {sel.get('Name','—')}")
        st.sidebar.markdown(f"**Marché :** {sel.get('Market','—')}")
        st.sidebar.markdown(f"**Secteur :** {sel.get('Sector','—')}")
        if 'Market Cap' in sel:
            st.sidebar.markdown(f"**Market Cap :** ${int(sel['Market Cap']):,}")
        st.sidebar.markdown(f"**Prix actuel :** ${sel.get('Price',0):.2f}")
        if 'Volume' in sel:
            st.sidebar.markdown(f"**Volume :** {int(sel['Volume']):,}")
        if "shortRatio" in sel:
            st.sidebar.markdown(f"**Short Ratio :** {sel['shortRatio']}")
        st.sidebar.markdown(f"[📎 Yahoo Finance](https://finance.yahoo.com/quote/{sel['Ticker']})")
else:
    if dataset_choice.startswith("Potentiels"):
        # Vue Potentiels
        cols = [c for c in ["Ticker","Name","Market","Sector","Market Cap","Price","Volume","ScorePotential","ScoreComposite","ReasonsTags","Comments","Status","Date"] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True)
    else:
        # Vue Analyses DS
        cols = [c for c in [
            "Ticker","Name","Market","Sector","Market Cap","Price","Volume",
            "ScorePotential","DS_Decision","DS_Confidence","DS_TargetPrice15d",
            "MeetsCriteria","DS_Conviction","DS_Catalyseurs","DS_Risks","DS_Timestamp"
        ] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True)

# === 7. Export CSV filtré
st.sidebar.markdown("---")
if st.sidebar.button("📤 Exporter en CSV"):
    if dataset_choice.startswith("Univers"):
        out = "filtered_microcaps.csv"
    elif dataset_choice.startswith("Potentiels"):
        out = "filtered_potentials.csv"
    else:
        out = "filtered_ds_analysis.csv"
    filtered.to_csv(out, index=False)
    st.sidebar.success(f"Export effectué : {out}")
