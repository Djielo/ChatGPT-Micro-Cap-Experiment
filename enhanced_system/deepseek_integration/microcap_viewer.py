import streamlit as st
import pandas as pd

# === 1. Chargement des données ===
@st.cache_data
def load_data():
    # Chargement avec parsing amélioré pour gérer les virgules dans les noms
    df = pd.read_csv("enhanced_system/data/micro_caps_extended.csv", 
                     quotechar='"', 
                     escapechar='\\', 
                     encoding='utf-8')
    
    # Vérification des colonnes attendues
    expected_columns = ["Ticker", "Name", "Market Cap", "Price", "Sector", "Market", "Volume", "shortRatio"]
    missing_columns = [col for col in expected_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Colonnes manquantes: {missing_columns}")
        st.write("Colonnes disponibles:", df.columns.tolist())
        return pd.DataFrame()
    
    # Nettoyage des données
    df = df.dropna(subset=["Market Cap", "Price", "Volume"])
    
    # Debug: afficher les premières lignes
    st.subheader("🔍 Aperçu des données chargées")
    st.write(f"📊 {len(df)} lignes chargées")
    st.write("Colonnes:", df.columns.tolist())
    st.write("Premières lignes:")
    st.dataframe(df.head())
    
    return df

df = load_data()

st.set_page_config(page_title="Microcap Viewer", layout="wide")

st.title("📊 Microcaps Viewer – Analyse et Scoring interactif")

# === 2. Sidebar : Filtres ===
st.sidebar.header("🔎 Filtres")

# Marché
markets = st.sidebar.multiselect("Marchés", options=sorted(df["Market"].dropna().unique()), default=sorted(df["Market"].dropna().unique()))

# Secteurs
sectors = st.sidebar.multiselect("Secteurs", options=sorted(df["Sector"].dropna().unique()), default=sorted(df["Sector"].dropna().unique()))

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
        cap_min = st.number_input("", min_value=0, max_value=100_000, value=74, label_visibility="collapsed")
    with col2:
        cap_max = st.number_input("", min_value=0, max_value=100_000, value=75, label_visibility="collapsed")
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
        price_min = st.number_input("", min_value=0.0, max_value=1000.0, value=1.0, step=0.1, label_visibility="collapsed")
    with col2:
        price_max = st.number_input("", min_value=0.0, max_value=1000.0, value=30.0, step=0.1, label_visibility="collapsed")
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
        volume_min = st.number_input("", min_value=0, max_value=100_000_000, value=1000, step=1000, label_visibility="collapsed")
    with col2:
        volume_max = st.number_input("", min_value=0, max_value=100_000_000, value=1000000, step=1000, label_visibility="collapsed")
    volume_range = (volume_min, volume_max)
else:
    volume_range = (0, float('inf'))

# Short Ratio
if "shortRatio" in df.columns:
    short_ratio_max = df["shortRatio"].max(skipna=True)
    if pd.notna(short_ratio_max):
        short_ratio_range = st.sidebar.slider("Short Ratio", 0.0, float(short_ratio_max), (0.0, float(short_ratio_max)))
    else:
        short_ratio_range = (0.0, 1.0)
else:
    short_ratio_range = (0.0, 1.0)

# === 3. Sidebar : Scoring ===
st.sidebar.header("📈 Poids du Scoring")

w_price = st.sidebar.slider("📉 Poids Prix (1/Prix)", 0.0, 10.0, 2.0)
w_volume = st.sidebar.slider("🔊 Poids Volume", 0.0, 10.0, 1.0)
w_cap = st.sidebar.slider("🏢 Poids Market Cap (inverse)", 0.0, 5.0, 0.5)
w_short = st.sidebar.slider("⚠️ Poids Short Ratio", 0.0, 10.0, 3.0) if "shortRatio" in df.columns else 0

# === 4. Application des filtres ===
filtered = df[
    df["Market"].isin(markets) &
    df["Sector"].isin(sectors) &
    df["Market Cap"].between(*cap_range) &
    df["Price"].between(*price_range) &
    df["Volume"].between(*volume_range)
]

if "shortRatio" in df.columns:
    filtered = filtered[filtered["shortRatio"].between(*short_ratio_range)]

# === 5. Calcul du Score ===
filtered["Score"] = (
    w_price / filtered["Price"].replace(0, 1) +
    w_volume * (filtered["Volume"] / 1_000_000) +
    w_cap / filtered["Market Cap"].replace(0, 1)
)

if "shortRatio" in df.columns:
    filtered["Score"] += w_short * filtered["shortRatio"].fillna(0)

# Nettoyer les scores NaN
filtered["Score"] = filtered["Score"].fillna(0)

filtered = filtered.sort_values("Score", ascending=False).reset_index(drop=True)

# === 6. Affichage tableau et détails ===
st.markdown(f"### 🎯 {len(filtered)} micro-caps affichées après filtrage")

selected_index = st.selectbox("Sélectionner une ligne pour détails 👇", range(len(filtered)), format_func=lambda i: filtered.iloc[i]["Ticker"] if len(filtered) > 0 else "—")

st.dataframe(filtered[["Ticker", "Name", "Market", "Sector", "Market Cap", "Price", "Volume", "shortRatio", "Score"]], use_container_width=True)

if len(filtered) > 0:
    selected_row = filtered.iloc[selected_index]
    st.sidebar.markdown("### 🧾 Détail de l'entreprise sélectionnée")
    st.sidebar.markdown(f"**Ticker :** `{selected_row['Ticker']}`")
    st.sidebar.markdown(f"**Nom :** {selected_row['Name']}")
    st.sidebar.markdown(f"**Marché :** {selected_row['Market']}")
    st.sidebar.markdown(f"**Secteur :** {selected_row['Sector']}")
    st.sidebar.markdown(f"**Market Cap :** ${int(selected_row['Market Cap']):,}")
    st.sidebar.markdown(f"**Prix actuel :** ${selected_row['Price']:.2f}")
    st.sidebar.markdown(f"**Volume :** {int(selected_row['Volume']):,}")
    if "shortRatio" in selected_row:
        st.sidebar.markdown(f"**Short Ratio :** {selected_row['shortRatio']}")
    st.sidebar.markdown(f"[📎 Lien Yahoo Finance](https://finance.yahoo.com/quote/{selected_row['Ticker']})")

# === 7. Export CSV filtré
st.sidebar.markdown("---")
if st.sidebar.button("📤 Exporter en CSV"):
    filtered.to_csv("filtered_microcaps.csv", index=False)
    st.sidebar.success("✅ Export effectué : filtered_microcaps.csv")
