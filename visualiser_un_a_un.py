import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

# Charger les données
df = pd.read_excel('COORDONNEES.xlsx')

# Nettoyer les données - remplir les valeurs manquantes pour les cyclones
df['Saison cyclonique'] = df['Saison cyclonique'].ffill()
df['Nom du cyclone'] = df['Nom du cyclone'].ffill()

# Convertir les colonnes de coordonnées en numérique
df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')

# Créer une colonne datetime complète
df['Date'] = pd.to_datetime(df['Date'])
df['Datetime'] = df['Date'] + pd.to_timedelta(df['Heure'], unit='h')

# Supprimer les lignes avec des dates ou coordonnées invalides
df = df.dropna(subset=['Datetime', 'Lat', 'Lon'])

# Fonction pour formater la date en toute sécurité
def safe_strftime(dt, fmt='%Y-%m-%d %H:%M'):
    """Formatte une date en gérant les valeurs NaT"""
    if pd.isna(dt):
        return 'Date inconnue'
    try:
        return dt.strftime(fmt)
    except:
        return 'Date invalide'

# Fonction pour créer la visualisation d'un seul cyclone
def plot_single_cyclone(cyclone_name):
    """
    Affiche le trajet d'un seul cyclone sur un globe terrestre
    
    Parameters:
    cyclone_name (str): Nom du cyclone à afficher
    """
    
    # Filtrer les données pour le cyclone sélectionné
    cyclone_data = df[df['Nom du cyclone'] == cyclone_name].sort_values('Datetime')
    
    if cyclone_data.empty:
        # Retourner une figure vide avec un message
        fig = go.Figure()
        fig.update_layout(
            title_text=f"Aucune donnée trouvée pour le cyclone {cyclone_name}",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{
                "text": "Aucune donnée disponible",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 28}
            }]
        )
        return fig, "Aucune information disponible"
    
    # Créer la figure
    fig = go.Figure()
    
    # Informations sur le cyclone
    saison = cyclone_data['Saison cyclonique'].iloc[0]
    duree_vie = cyclone_data['Durée de vie'].iloc[0] if 'Durée de vie' in cyclone_data.columns else "Non spécifiée"
    start_date = safe_strftime(cyclone_data['Datetime'].min())
    end_date = safe_strftime(cyclone_data['Datetime'].max())
    nb_points = len(cyclone_data)
    
    info_text = f"""
    - Cyclone: {cyclone_name}  
    - Saison: {saison}  
    - Durée de vie: {duree_vie}  
    - Période: {start_date} à {end_date}  
    - Nombre de points de trajet: {nb_points}
    """
    
    # Préparer le texte pour le hover
    hover_text = []
    for _, row in cyclone_data.iterrows():
        date_str = safe_strftime(row['Datetime'])
        hover_text.append(
            f"Cyclone: {cyclone_name}<br>"
            f"Date: {date_str}<br>"
            f"Heure: {row['Heure']}h<br>"
            f"Position: ({row['Lat']:.2f}°, {row['Lon']:.2f}°)"
        )
    
    # Tracer la ligne du trajet
    fig.add_trace(go.Scattergeo(
        lon=cyclone_data['Lon'],
        lat=cyclone_data['Lat'],
        mode='lines+markers',
        line=dict(width=4, color='red'),
        marker=dict(size=8, color='red'),
        name=cyclone_name,
        text=hover_text,
        hoverinfo='text'
    ))
    
    # Ajouter le point de départ
    start_point = cyclone_data.iloc[0]
    start_date_str = safe_strftime(start_point['Datetime'])
    fig.add_trace(go.Scattergeo(
        lon=[start_point['Lon']],
        lat=[start_point['Lat']],
        mode='markers',
        marker=dict(size=15, color='green', symbol='star'),
        name="Début",
        text=f"Début: {start_date_str}",
        hoverinfo='text',
        showlegend=True
    ))
    
    # Ajouter le point d'arrivée
    end_point = cyclone_data.iloc[-1]
    end_date_str = safe_strftime(end_point['Datetime'])
    fig.add_trace(go.Scattergeo(
        lon=[end_point['Lon']],
        lat=[end_point['Lat']],
        mode='markers',
        marker=dict(size=15, color='blue', symbol='x'),
        name="Fin",
        text=f"Fin: {end_date_str}",
        hoverinfo='text',
        showlegend=True
    ))
    
    # Calculer les limites de la carte pour zoomer sur le trajet
    lat_margin = (cyclone_data['Lat'].max() - cyclone_data['Lat'].min()) * 0.2
    lon_margin = (cyclone_data['Lon'].max() - cyclone_data['Lon'].min()) * 0.2
    
    lat_range = [
        max(cyclone_data['Lat'].min() - lat_margin, -60),
        min(cyclone_data['Lat'].max() + lat_margin, 10)
    ]
    lon_range = [
        max(cyclone_data['Lon'].min() - lon_margin, 20),
        min(cyclone_data['Lon'].max() + lon_margin, 120)
    ]
    
    # Configuration du layout
    fig.update_layout(
        title_text=f'Trajet du Cyclone {cyclone_name}',
        showlegend=True,
        geo=dict(
            scope='world',
            projection_type='mercator',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            showocean=True,
            oceancolor='rgb(200, 230, 255)',
            lataxis=dict(range=lat_range),
            lonaxis=dict(range=lon_range),
        ),
        height=700,
        width=1000
    )
    
    return fig, info_text

# Fonction pour visualiser tous les cyclones
def plot_all_cyclones():
    """Affiche tous les cyclones sur la même carte"""
    
    # Créer la figure
    fig = go.Figure()
    
    # Couleurs pour différents cyclones
    colors = px.colors.qualitative.Set1
    
    # Grouper par cyclone et tracer chaque trajet
    cyclones = df['Nom du cyclone'].unique()
    
    for i, cyclone in enumerate(cyclones):
        cyclone_data = df[df['Nom du cyclone'] == cyclone].sort_values('Datetime')
        color = colors[i % len(colors)]
        
        # Tracer la ligne du trajet
        fig.add_trace(go.Scattergeo(
            lon=cyclone_data['Lon'],
            lat=cyclone_data['Lat'],
            mode='lines',
            line=dict(width=2, color=color),
            name=cyclone,
            showlegend=True
        ))
    
    # Configuration du layout
    fig.update_layout(
        title_text='Tous les Cyclones - Vue d\'ensemble',
        showlegend=True,
        geo=dict(
            scope='world',
            projection_type='mercator',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            showocean=True,
            oceancolor='rgb(200, 230, 255)',
            lataxis=dict(range=[-60, 10]),
            lonaxis=dict(range=[20, 120]),
        ),
        height=700,
        width=1000
    )
    
    return fig, f"Affichage de {len(cyclones)} cyclones"

# Initialiser l'application Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Visualisation des Cyclones"

# Obtenir la liste des cyclones
cyclones_list = sorted(df['Nom du cyclone'].unique())

# Layout de l'application
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🌪️ Visualisation des Cyclones", 
                   className="text-center mb-4",
                   style={'color': '#2c3e50'})
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Label("Sélectionnez un cyclone:", 
                      className="fw-bold",
                      style={'fontSize': '18px'}),
            dcc.Dropdown(
                id='cyclone-dropdown',
                options=[{'label': cyclone, 'value': cyclone} for cyclone in cyclones_list],
                value=cyclones_list[0] if cyclones_list else None,
                placeholder="Choisissez un cyclone...",
                style={'fontSize': '16px'}
            )
        ], width=6),
        
        dbc.Col([
            dbc.Button("Voir tous les cyclones", 
                      id='show-all-button',
                      color="primary",
                      className="me-2",
                      style={'fontSize': '16px', 'marginTop': '25px'}),
            dbc.Button("Réinitialiser", 
                      id='reset-button',
                      color="secondary",
                      style={'fontSize': '16px', 'marginTop': '25px'})
        ], width=6, className="d-flex align-items-end")
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Informations du Cyclone", 
                              className="fw-bold",
                              style={'fontSize': '18px', 'backgroundColor': '#f8f9fa'}),
                dbc.CardBody([
                    html.Div(id='cyclone-info', 
                            style={'fontSize': '16px', 'whiteSpace': 'pre-wrap'})
                ])
            ])
        ], width=4),
        
        dbc.Col([
            dcc.Graph(id='cyclone-map')
        ], width=8)
    ]),
    
    # Store pour garder l'état actuel
    dcc.Store(id='current-view', data='single')
    
], fluid=True)

# Callbacks
@app.callback(
    [Output('cyclone-map', 'figure'),
     Output('cyclone-info', 'children'),
     Output('current-view', 'data')],
    [Input('cyclone-dropdown', 'value'),
     Input('show-all-button', 'n_clicks'),
     Input('reset-button', 'n_clicks')],
    [State('current-view', 'data')]
)
def update_cyclone_display(selected_cyclone, show_all_clicks, reset_clicks, current_view):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Premier chargement
        fig, info = plot_single_cyclone(selected_cyclone)
        return fig, info, 'single'
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'show-all-button':
        fig, info = plot_all_cyclones()
        return fig, info, 'all'
    
    elif trigger_id == 'reset-button':
        fig, info = plot_single_cyclone(selected_cyclone)
        return fig, info, 'single'
    
    else:  # cyclone-dropdown
        fig, info = plot_single_cyclone(selected_cyclone)
        return fig, info, 'single'

# Fonction utilitaire pour lister tous les cyclones
def list_all_cyclones():
    """Retourne la liste de tous les cyclones disponibles"""
    return df['Nom du cyclone'].unique().tolist()

# Exécuter l'application
if __name__ == '__main__':
    print("Cyclones disponibles:", list_all_cyclones())
    print("Lancement de l'application Dash...")
    print("Ouvrez votre navigateur et allez à l'adresse: http://127.0.0.1:8050/")
    
    # CORRECTION : Utiliser app.run() au lieu de app.run_server()
    app.run(debug=True, host='127.0.0.1', port=8050)