import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import os

# === 1. Fonctions de chargement des données ===
def load_universe():
    """Charge les données de l'univers microcaps"""
    try:
        df = pd.read_csv('../data/micro_caps_extended.csv')
        return df
    except FileNotFoundError:
        # Retourner un DataFrame vide avec les colonnes attendues
        return pd.DataFrame(columns=['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume'])

def load_potentials():
    """Charge les données des potentiels"""
    try:
        df = pd.read_csv('../data/extended_to_potential.csv')
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume'])

def load_ds_analysis():
    """Charge les données des analyses DS"""
    try:
        df = pd.read_csv('../data/potential_to_pepite.csv')
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume'])

def load_final_pepites():
    """Charge les données des final pepites"""
    try:
        df = pd.read_csv('../data/pepite_to_sharpratio.csv')
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume'])

# === 2. Layout Dash ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)

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
    
    # États des menus (cachés)
    dcc.Store(id='controls-expanded', data=True),
    dcc.Store(id='filters-expanded', data=True),
    dcc.Store(id='numeric-expanded', data=True),
    dcc.Store(id='scoring-expanded', data=True),
    
    # Contrôles principaux
    html.Div([
        # Colonne 1: Contrôles
        html.Div([
            html.H3("🎛️ Contrôles", id='controls-title', style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px', 'cursor': 'pointer'}),
            html.Div(id='controls-content', children=[
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
            ])
        ], style={'width': '20%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #60a5fa', 'borderRadius': '14px', 'marginRight': '10px'}),
        
        # Colonne 2: Filtres
        html.Div([
            html.H3("🔍 Filtres", id='filters-title', style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px', 'cursor': 'pointer'}),
            html.Div(id='filters-content', children=[
                html.Div([
                    html.Div([
                        html.Div(html.Label("Marchés:", style={'color': '#f472b6', 'fontWeight': 'bold'}), style={'marginBottom': '8px'}),
                        dcc.Checklist(
                            id='markets-filter',
                            options=[],
                            value=[],
                            style={'color': 'white'},
                            labelStyle={'marginBottom': '6px'}
                        )
                    ], style={'width': '33%'}),
                    html.Div([
                        html.Div(html.Label("Secteurs:", style={'color': '#f472b6', 'fontWeight': 'bold'}), style={'marginBottom': '8px'}),
                        html.Div([
                            html.Div([
                                dcc.Checklist(
                                    id='sectors-filter-col1',
                                    options=[],
                                    value=[],
                                    style={'color': 'white'},
                                    labelStyle={'marginBottom': '6px'}
                                )
                            ], style={'width': '50%'}),
                            html.Div([
                                dcc.Checklist(
                                    id='sectors-filter-col2',
                                    options=[],
                                    value=[],
                                    style={'color': 'white'},
                                    labelStyle={'marginBottom': '6px'}
                                )
                            ], style={'width': '50%'})
                        ], style={'display': 'flex'})
                    ], style={'width': '67%'})
                ], style={'display': 'flex'})
            ])
        ], style={'width': '40%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #f472b6', 'borderRadius': '14px', 'marginRight': '10px'}),
        
        # Colonne 3: Filtres numériques
        html.Div([
            html.H3("📊 Filtres numériques", id='numeric-title', style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px', 'cursor': 'pointer'}),
            html.Div(id='numeric-content', children=[
                html.Div([
                    html.Div(html.Label("Market Cap (M$):", style={'color': '#a78bfa'}), style={'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(id='cap-min', type='number', value=74, style={'width': '45%', 'marginRight': '5%'}),
                        html.Span("à", style={'color': 'white', 'marginRight': '5%'}),
                        dcc.Input(id='cap-max', type='number', value=75, style={'width': '45%'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Div(html.Label("Prix ($):", style={'color': '#a78bfa'}), style={'marginBottom': '8px'}),
                    html.Div([
                        dcc.Input(id='price-min', type='number', value=1, step=0.1, style={'width': '45%', 'marginRight': '5%'}),
                        html.Span("à", style={'color': 'white', 'marginRight': '5%'}),
                        dcc.Input(id='price-max', type='number', value=30, step=0.1, style={'width': '45%'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px'}),
                html.Div([
                    html.Div(html.Label("Volume:", style={'color': '#a78bfa'}), style={'marginBottom': '8px'}),
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
            html.H3("📈 Poids du Scoring", id='scoring-title', style={'color': 'white', 'marginBottom': '15px', 'marginTop': '0px', 'cursor': 'pointer'}),
            html.Div(id='scoring-content', children=[
                html.Div(id='scoring-weights')
            ])
        ], style={'width': '20%', 'padding': '15px', 'backgroundColor': 'rgba(17,24,39,0.75)', 'border': '1px solid #34d399', 'borderRadius': '14px'})
    ], style={'display': 'flex', 'marginBottom': '20px'}),
    
    # Tableau des résultats
    html.Div([
        html.H3("🎯 Résultats", style={'color': 'white', 'marginBottom': '15px'}),
        html.Div(id='results-table', style={'backgroundColor': 'rgba(17,24,39,0.75)', 'borderRadius': '8px', 'padding': '15px'}),
        # Pagination
        html.Div([
            html.Button("◀ Précédent", id='prev-page', 
                       style={'marginRight': '10px', 'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'}),
            html.Span(id='page-info', style={'color': 'white', 'marginRight': '10px'}),
            html.Button("Suivant ▶", id='next-page',
                       style={'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'})
        ], id='pagination-controls', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginTop': '15px'}),
        # Page actuelle (cachée)
        dcc.Store(id='current-page', data=0)
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
            html.Label("Prix:", style={'color': '#34d399'}),
            dcc.Slider(id='w-price', min=0, max=10, value=2, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Volume:", style={'color': '#34d399'}),
            dcc.Slider(id='w-volume', min=0, max=10, value=1, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Market Cap:", style={'color': '#34d399'}),
            dcc.Slider(id='w-cap', min=0, max=5, value=0.5, step=0.1, marks={i: str(i) for i in range(0, 6, 1)})
        ]
    else:
        # Pour les autres datasets, on peut ajouter des poids spécifiques
        scoring_weights = [
            html.Label("Prix:", style={'color': '#34d399'}),
            dcc.Slider(id='w-price', min=0, max=10, value=2, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Volume:", style={'color': '#34d399'}),
            dcc.Slider(id='w-volume', min=0, max=10, value=1, step=0.1, marks={i: str(i) for i in range(0, 11, 2)}),
            html.Label("Market Cap:", style={'color': '#34d399'}),
            dcc.Slider(id='w-cap', min=0, max=5, value=0.5, step=0.1, marks={i: str(i) for i in range(0, 6, 1)}),
            html.Label("Confiance DS:", style={'color': '#34d399'}),
            dcc.Slider(id='w-confidence', min=0, max=10, value=5, step=0.1, marks={i: str(i) for i in range(0, 11, 2)})
        ]
    
    return market_options, sector_col1, sector_col2, scoring_weights

@app.callback(
    [Output('results-table', 'children'),
     Output('current-page', 'data'),
     Output('prev-page', 'style'),
     Output('next-page', 'style')],
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
     Input('prev-page', 'n_clicks'),
     Input('next-page', 'n_clicks')],
    [State('current-page', 'data')]
)
def update_results(dataset_choice, markets, sectors_col1, sectors_col2, cap_min, cap_max, price_min, price_max, volume_min, volume_max, prev_clicks, next_clicks, current_page):
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
    
    # Calcul du score pour l'univers (pour l'instant sans les poids)
    if dataset_choice == 'univers':
        # TODO: Réintégrer les poids quand on aura résolu le problème des callbacks
        filtered['Score'] = (
            2 / filtered['Price'].replace(0, 1) +
            1 * (filtered['Volume'] / 1_000_000) +
            0.5 / filtered['Market Cap'].replace(0, 1)
        )
        filtered = filtered.sort_values('Score', ascending=False)
    
    # Gérer la pagination
    page_size = 20
    total_pages = (len(filtered) + page_size - 1) // page_size
    
    # Déterminer la page actuelle
    if current_page is None:
        current_page = 0
    else:
        # Gérer les clics sur les boutons
        # On utilise triggered_id pour savoir quel bouton a été cliqué
        from dash import ctx
        if ctx.triggered_id == 'prev-page' and current_page > 0:
            current_page = current_page - 1
        elif ctx.triggered_id == 'next-page' and current_page < total_pages - 1:
            current_page = current_page + 1
    
    # Créer le tableau
    if len(filtered) > 0:
        # Colonnes disponibles dans le dataset
        available_cols = ['Ticker', 'Name', 'Market', 'Sector', 'Market Cap', 'Price', 'Volume']
        cols = [col for col in available_cols if col in filtered.columns]
        if 'Score' in filtered.columns:
            cols.append('Score')
        
        # Paginer les données
        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        table_data = filtered[cols].iloc[start_idx:end_idx].to_dict('records')
        
        # Styles pour les boutons de pagination
        prev_style = {'marginRight': '10px', 'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px', 'display': 'none'} if current_page == 0 else {'marginRight': '10px', 'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'}
        next_style = {'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px', 'display': 'none'} if current_page >= total_pages - 1 else {'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px'}
        
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
            ], style={'width': '100%', 'borderCollapse': 'collapse'}),
            # Info de pagination
            html.Div([
                html.Span(f"Page {current_page + 1} sur {total_pages} (lignes {start_idx + 1}-{min(end_idx, len(filtered))})", 
                         id='page-info', style={'color': 'white'})
            ], style={'textAlign': 'center', 'marginTop': '10px'})
        ], current_page, prev_style, next_style
    else:
        # Si aucun résultat, cacher les deux boutons
        hidden_style = {'backgroundColor': '#4a5568', 'color': 'white', 'border': 'none', 'padding': '8px 16px', 'borderRadius': '4px', 'display': 'none'}
        return html.H4("Aucun résultat trouvé", style={'color': 'white'}), current_page, hidden_style, hidden_style

# Callbacks pour les menus collapsibles
@app.callback(
    [Output('controls-content', 'style'),
     Output('filters-content', 'style'),
     Output('numeric-content', 'style'),
     Output('scoring-content', 'style')],
    [Input('controls-title', 'n_clicks'),
     Input('filters-title', 'n_clicks'),
     Input('numeric-title', 'n_clicks'),
     Input('scoring-title', 'n_clicks'),
     Input('toggle-all', 'n_clicks')],
    [State('controls-expanded', 'data'),
     State('filters-expanded', 'data'),
     State('numeric-expanded', 'data'),
     State('scoring-expanded', 'data')]
)
def toggle_menus(controls_clicks, filters_clicks, numeric_clicks, scoring_clicks, toggle_all_clicks,
                 controls_expanded, filters_expanded, numeric_expanded, scoring_expanded):
    from dash import ctx
    
    # Initialiser les états si None
    if controls_expanded is None: controls_expanded = True
    if filters_expanded is None: filters_expanded = True
    if numeric_expanded is None: numeric_expanded = True
    if scoring_expanded is None: scoring_expanded = True
    
    # Gérer le bouton global
    if ctx.triggered_id == 'toggle-all':
        # Inverser tous les états
        controls_expanded = not controls_expanded
        filters_expanded = not filters_expanded
        numeric_expanded = not numeric_expanded
        scoring_expanded = not scoring_expanded
    else:
        # Gérer les clics individuels
        if ctx.triggered_id == 'controls-title':
            controls_expanded = not controls_expanded
        elif ctx.triggered_id == 'filters-title':
            filters_expanded = not filters_expanded
        elif ctx.triggered_id == 'numeric-title':
            numeric_expanded = not numeric_expanded
        elif ctx.triggered_id == 'scoring-title':
            scoring_expanded = not scoring_expanded
    
    # Retourner les styles
    controls_style = {'display': 'block'} if controls_expanded else {'display': 'none'}
    filters_style = {'display': 'block'} if filters_expanded else {'display': 'none'}
    numeric_style = {'display': 'block'} if numeric_expanded else {'display': 'none'}
    scoring_style = {'display': 'block'} if scoring_expanded else {'display': 'none'}
    
    return controls_style, filters_style, numeric_style, scoring_style

if __name__ == '__main__':
    app.run(debug=True, port=8050)
