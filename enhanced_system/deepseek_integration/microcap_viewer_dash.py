import dash
from dash import dcc, html, Input, Output, State, callback
import pandas as pd
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate

# Initialiser l'app Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# === 1. Fonctions de chargement des données (identiques à Streamlit) ===
def load_universe():
    df = pd.read_csv(
        "../data/micro_caps_extended.csv",
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
        print(f"❌ Colonnes manquantes: {missing}")
        return pd.DataFrame()
    return df.dropna(subset=["Market Cap", "Price", "Volume"])

def load_potentials():
    df = pd.read_csv(
        "../data/extended_to_potential.csv",
        encoding='utf-8',
    )
    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})
    if "Exchange" in df.columns and "Market" not in df.columns:
        df = df.rename(columns={"Exchange": "Market"})
    if "CompanyName" in df.columns and "Name" not in df.columns:
        df = df.rename(columns={"CompanyName": "Name"})
    return df

def load_ds_analysis():
    df = pd.read_csv(
        "../data/potential_to_pepite.csv",
        encoding='utf-8',
    )
    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})
    if "Exchange" in df.columns and "Market" not in df.columns:
        df = df.rename(columns={"Exchange": "Market"})
    if "CompanyName" in df.columns and "Name" not in df.columns:
        df = df.rename(columns={"CompanyName": "Name"})
    return df

def load_final_pepites():
    df = pd.read_csv(
        "../data/pepite_to_sharpratio.csv",
        encoding='utf-8',
    )
    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})
    if "Exchange" in df.columns and "Market" not in df.columns:
        df = df.rename(columns={"Exchange": "Market"})
    if "CompanyName" in df.columns and "Name" not in df.columns:
        df = df.rename(columns={"CompanyName": "Name"})
    return df

# === 2. Layout Dash ===
app.layout = html.Div([

    
    # Header
    html.Div([
        html.H1("📊 Microcaps Viewer – Analyse et Scoring interactif", 
                style={'margin': '0', 'color': 'white'}),
        html.Div([
            html.Button("🔄 Ouvrir/Fermer tous les menus", id='toggle-all', 
                       style={'marginRight': '10px', 'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'}),
            html.Button("📤 Export CSV", id='export-csv',
                       style={'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'})
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '20px', 'padding': '20px', 'backgroundColor': '#1a202c', 'borderRadius': '8px'}),
    
    # Contrôles principaux
    html.Div([
        # Colonne 1: Contrôles
        html.Div([
            html.H3("🎛️ Contrôles", style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px'}),
            dcc.RadioItems(
                id='dataset-choice',
                options=[
                    {'label': 'Univers (micro_caps_extended)', 'value': 'univers'},
                    {'label': 'Potentiels (extended_to_potential)', 'value': 'potentiels'},
                    {'label': 'Analyses DS (potential_to_pepite)', 'value': 'analyses_ds'},
                    {'label': 'Final Pepites (pepite_to_sharpratio)', 'value': 'final_pepites'}
                ],
                value='univers',
                style={'color': 'white'},
                labelStyle={'marginBottom': '8px'}
            )
        ], style={'width': '20%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #60a5fa', 'borderRadius': '14px', 'marginRight': '10px'}),
        
        # Colonne 2: Filtres
        html.Div([
            html.H3("🔍 Filtres", style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px'}),
            html.Div([
                html.Div([
                    html.Label("Marchés:", style={'color': 'white', 'fontWeight': 'bold'}),
                    dcc.Checklist(
                        id='markets-filter',
                        options=[],  # Sera rempli dynamiquement
                        value=[],
                        style={'color': 'white'},
                        labelStyle={'marginBottom': '6px'}
                    )
                ], style={'width': '33%'}),
                html.Div([
                    html.Label("Secteurs:", style={'color': 'white', 'fontWeight': 'bold'}),
                    html.Div([
                        html.Div([
                            dcc.Checklist(
                                id='sectors-filter-col1',
                                options=[],  # Sera rempli dynamiquement
                                value=[],
                                style={'color': 'white'},
                                labelStyle={'marginBottom': '6px'}
                            )
                        ], style={'width': '50%'}),
                        html.Div([
                            dcc.Checklist(
                                id='sectors-filter-col2',
                                options=[],  # Sera rempli dynamiquement
                                value=[],
                                style={'color': 'white'},
                                labelStyle={'marginBottom': '6px'}
                            )
                        ], style={'width': '50%'})
                    ], style={'display': 'flex'})
                ], style={'width': '67%'})
            ], style={'display': 'flex'})
        ], style={'width': '40%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #f472b6', 'borderRadius': '14px', 'marginRight': '10px'}),
        
        # Colonne 3: Filtres numériques
        html.Div([
            html.H3("📊 Filtres numériques", style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px'}),
            html.Div([
                html.Div([
                    html.Label("Market Cap (M$):", style={'color': 'white', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(id='cap-min', type='number', value=74, style={'width': '45%', 'marginRight': '5%'}),
                        html.Span("à", style={'color': 'white', 'marginRight': '5%'}),
                        dcc.Input(id='cap-max', type='number', value=75, style={'width': '45%'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Label("Prix ($):", style={'color': 'white', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(id='price-min', type='number', value=1, step=0.1, style={'width': '45%', 'marginRight': '5%'}),
                        html.Span("à", style={'color': 'white', 'marginRight': '5%'}),
                        dcc.Input(id='price-max', type='number', value=30, step=0.1, style={'width': '45%'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Label("Volume:", style={'color': 'white', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(id='volume-min', type='number', value=1000, style={'width': '45%', 'marginRight': '5%'}),
                        html.Span("à", style={'color': 'white', 'marginRight': '5%'}),
                        dcc.Input(id='volume-max', type='number', value=1000000, style={'width': '45%'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px'})
            ])
        ], style={'width': '20%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #a78bfa', 'borderRadius': '14px', 'marginRight': '10px'}),
        
        # Colonne 4: Poids du Scoring
        html.Div([
            html.H3("📈 Poids du Scoring", style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px'}),
            html.Div(id='scoring-weights')
        ], style={'width': '20%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #34d399', 'borderRadius': '14px'})
    ], style={'display': 'flex', 'marginBottom': '20px'}),
    
    # Tableau des résultats
    html.Div([
        html.H3("🎯 Résultats", style={'color': 'white', 'marginBottom': '15px'}),
        html.Div(id='results-table', style={'backgroundColor': 'rgba(17,24,39,0.75)', 'borderRadius': '8px', 'padding': '15px'})
    ])
], style={'backgroundColor': '#0f1419', 'minHeight': '100vh', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# === 3. Callbacks Dash ===
@app.callback(
    [Output('markets-filter', 'options'),
     Output('sectors-filter-col1', 'options'),
     Output('sectors-filter-col2', 'options'),
     Output('scoring-weights', 'children')],
    [Input('dataset-choice', 'value')]
)
def update_filter_options(dataset_choice):
    # Charger les données selon le choix
    if dataset_choice == 'univers':
        df = load_universe()
    elif dataset_choice == 'potentiels':
        df = load_potentials()
    elif dataset_choice == 'analyses_ds':
        df = load_ds_analysis()
    else:
        df = load_final_pepites()
    
    # Options pour les marchés
    market_options = [{'label': market, 'value': market} for market in sorted(df['Market'].dropna().unique())] if 'Market' in df.columns else []
    
    # Options pour les secteurs (divisées en 2 colonnes)
    sector_options = [{'label': sector, 'value': sector} for sector in sorted(df['Sector'].dropna().unique())] if 'Sector' in df.columns else []
    mid_point = len(sector_options) // 2
    sector_col1 = sector_options[:mid_point]
    sector_col2 = sector_options[mid_point:]
    
    # Poids du scoring selon le dataset
    if dataset_choice == 'univers':
        scoring_weights = [
            html.Label("Prix:", style={'color': 'white'}),
            dcc.Slider(id='w-price', min=0, max=10, value=2, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Volume:", style={'color': 'white'}),
            dcc.Slider(id='w-volume', min=0, max=10, value=1, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Market Cap:", style={'color': 'white'}),
            dcc.Slider(id='w-cap', min=0, max=5, value=0.5, step=0.1, marks={i: str(i) for i in range(0, 6, 1)})
        ]
    else:
        # Pour les autres datasets, on peut ajouter des poids spécifiques
        scoring_weights = [
            html.Label("Prix:", style={'color': 'white'}),
            dcc.Slider(id='w-price', min=0, max=10, value=2, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Volume:", style={'color': 'white'}),
            dcc.Slider(id='w-volume', min=0, max=10, value=1, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Market Cap:", style={'color': 'white'}),
            dcc.Slider(id='w-cap', min=0, max=5, value=0.5, step=0.1, marks={i: str(i) for i in range(0, 6, 1)}),
            html.Label("Confiance DS:", style={'color': 'white'}),
            dcc.Slider(id='w-confidence', min=0, max=10, value=5, step=0.1, marks={i: str(i) for i in range(0, 11, 2)})
        ]
    
    return market_options, sector_col1, sector_col2, scoring_weights

@app.callback(
    Output('results-table', 'children'),
    [Input('dataset-choice', 'value'),
     Input('markets-filter', 'value'),
     Input('sectors-filter-col1', 'value'),
     Input('sectors-filter-col2', 'value'),
     Input('cap-min', 'value'),
     Input('cap-max', 'value'),
     Input('price-min', 'value'),
     Input('price-max', 'value'),
     Input('volume-min', 'value'),
     Input('volume-max', 'value'),
     Input('w-price', 'value'),
     Input('w-volume', 'value'),
     Input('w-cap', 'value')]
)
def update_results(dataset_choice, markets, sectors_col1, sectors_col2, cap_min, cap_max, price_min, price_max, volume_min, volume_max, w_price, w_volume, w_cap):
    # Charger les données
    if dataset_choice == 'univers':
        df = load_universe()
    elif dataset_choice == 'potentiels':
        df = load_potentials()
    elif dataset_choice == 'analyses_ds':
        df = load_ds_analysis()
    else:
        df = load_final_pepites()
    
    # Appliquer les filtres
    filtered = df.copy()
    
    if markets and 'Market' in filtered.columns:
        filtered = filtered[filtered['Market'].isin(markets)]
    
    # Combiner les secteurs des deux colonnes
    sectors = (sectors_col1 or []) + (sectors_col2 or [])
    if sectors and 'Sector' in filtered.columns:
        filtered = filtered[filtered['Sector'].isin(sectors)]
    
    if 'Market Cap' in filtered.columns and cap_min is not None and cap_max is not None:
        cap_min_val = cap_min * 1_000_000
        cap_max_val = cap_max * 1_000_000
        filtered = filtered[filtered['Market Cap'].between(cap_min_val, cap_max_val)]
    
    if 'Price' in filtered.columns and price_min is not None and price_max is not None:
        filtered = filtered[filtered['Price'].between(price_min, price_max)]
    
    if 'Volume' in filtered.columns and volume_min is not None and volume_max is not None:
        filtered = filtered[filtered['Volume'].between(volume_min, volume_max)]
    
    # Calcul du score pour l'univers
    if dataset_choice == 'univers':
        filtered['Score'] = (
            w_price / filtered['Price'].replace(0, 1) +
            w_volume * (filtered['Volume'] / 1_000_000) +
            w_cap / filtered['Market Cap'].replace(0, 1)
        )
        filtered = filtered.sort_values('Score', ascending=False)
    
    # Créer le tableau
    if len(filtered) > 0:
        # Colonnes disponibles dans le dataset
        available_cols = ['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume']
        cols = [col for col in available_cols if col in filtered.columns]
        if 'Score' in filtered.columns:
            cols.append('Score')
        
        table_data = filtered[cols].head(20).to_dict('records')
        
        return [
            html.H4(f"📊 {len(filtered)} lignes affichées après filtrage", style={'color': 'white'}),
            html.Table([
                html.Thead([
                    html.Tr([html.Th(col, style={'color': 'white', 'padding': '8px'}) for col in cols])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(str(row[col]), style={'color': 'white', 'padding': '8px'}) 
                        for col in cols
                    ]) for row in table_data
                ])
            ], style={'width': '100%', 'borderCollapse': 'collapse'})
        ]
    else:
        return html.H4("Aucun résultat trouvé", style={'color': 'white'})

if __name__ == '__main__':
    app.run(debug=True, port=8050)
