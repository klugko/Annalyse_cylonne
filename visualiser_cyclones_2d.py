import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

# Fonction pour créer la visualisation
def plot_cyclones_tracks(cyclone_names=None):
    """
    Affiche les trajets des cyclones sur un globe terrestre
    
    Parameters:
    cyclone_names (list): Liste des noms de cyclones à afficher. Si None, affiche tous.
    """
    
    # Filtrer par cyclones spécifiques si demandé
    if cyclone_names:
        filtered_df = df[df['Nom du cyclone'].isin(cyclone_names)].copy()
    else:
        filtered_df = df.copy()
    
    # Créer la figure
    fig = go.Figure()
    
    # Couleurs pour différents cyclones
    colors = px.colors.qualitative.Set1
    
    # Grouper par cyclone et tracer chaque trajet
    cyclones = filtered_df['Nom du cyclone'].unique()
    
    for i, cyclone in enumerate(cyclones):
        cyclone_data = filtered_df[filtered_df['Nom du cyclone'] == cyclone].sort_values('Datetime')
        color = colors[i % len(colors)]
        
        # Préparer le texte pour le hover
        hover_text = []
        for _, row in cyclone_data.iterrows():
            date_str = safe_strftime(row['Datetime'])
            hover_text.append(
                f"Cyclone: {cyclone}<br>"
                f"Date: {date_str}<br>"
                f"Position: ({row['Lat']:.2f}, {row['Lon']:.2f})"
            )
        
        # Tracer la ligne du trajet
        fig.add_trace(go.Scattergeo(
            lon=cyclone_data['Lon'],
            lat=cyclone_data['Lat'],
            mode='lines+markers',
            line=dict(width=3, color=color),
            marker=dict(size=6, color=color),
            name=cyclone,
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
            marker=dict(size=10, color=color, symbol='star'),
            name=f"{cyclone} - Début",
            text=f"Début: {start_date_str}",
            hoverinfo='text',
            showlegend=False
        ))
        
        # Ajouter le point d'arrivée
        end_point = cyclone_data.iloc[-1]
        end_date_str = safe_strftime(end_point['Datetime'])
        fig.add_trace(go.Scattergeo(
            lon=[end_point['Lon']],
            lat=[end_point['Lat']],
            mode='markers',
            marker=dict(size=10, color=color, symbol='x'),
            name=f"{cyclone} - Fin",
            text=f"Fin: {end_date_str}",
            hoverinfo='text',
            showlegend=False
        ))
    
    # Configuration du layout
    fig.update_layout(
        title_text='Trajets des Cyclones - Océan Indien Sud',
        showlegend=True,
        geo=dict(
            scope='world',
            projection_type='mercator',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            lataxis=dict(range=[-60, 10]),  # Focus sur l'océan Indien
            lonaxis=dict(range=[20, 120]),
        ),
        height=800,
        width=1200
    )
    
    return fig

# Fonction pour visualiser un cyclone spécifique avec animation temporelle
def plot_cyclone_animation(cyclone_name):
    """
    Affiche un cyclone spécifique avec animation de son trajet dans le temps
    """
    cyclone_data = df[df['Nom du cyclone'] == cyclone_name].sort_values('Datetime')
    
    if cyclone_data.empty:
        print(f"Aucune donnée trouvée pour le cyclone {cyclone_name}")
        return None
    
    fig = go.Figure()
    
    # Tracer le trajet complet en fond
    fig.add_trace(go.Scattergeo(
        lon=cyclone_data['Lon'],
        lat=cyclone_data['Lat'],
        mode='lines',
        line=dict(width=2, color='gray'),
        name='Trajet complet',
        showlegend=False
    ))
    
    # Ajouter l'animation
    frames = []
    for i, (idx, row) in enumerate(cyclone_data.iterrows()):
        frame = go.Frame(
            data=[
                go.Scattergeo(
                    lon=cyclone_data['Lon'].iloc[:i+1],
                    lat=cyclone_data['Lat'].iloc[:i+1],
                    mode='lines+markers',
                    line=dict(width=3, color='red'),
                    marker=dict(size=8, color='red')
                )
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # Préparer les étapes du slider avec gestion sécurisée des dates
    steps = []
    for i, (idx, row) in enumerate(cyclone_data.iterrows()):
        date_str = safe_strftime(row['Datetime'], '%m-%d %Hh')
        step = {
            'args': [[f'frame_{i}'], {'frame': {'duration': 500, 'redraw': True}, 'mode': 'immediate'}],
            'label': date_str,
            'method': 'animate'
        }
        steps.append(step)
    
    sliders = [{
        'steps': steps,
        'transition': {'duration': 300},
        'x': 0.1, 'len': 0.9,
        'currentvalue': {'font': {'size': 12}, 'prefix': 'Date: ', 'visible': True, 'xanchor': 'center'},
        'pad': {'b': 10, 't': 50}
    }]
    
    fig.update_layout(
        title_text=f'Trajet du Cyclone {cyclone_name} - Animation Temporelle',
        geo=dict(
            scope='world',
            projection_type='mercator',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            lataxis=dict(range=[-60, 10]),
            lonaxis=dict(range=[20, 120]),
        ),
        updatemenus=[{
            'type': 'buttons',
            'buttons': [
                {
                    'args': [None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}],
                    'label': 'Play',
                    'method': 'animate'
                },
                {
                    'args': [[None], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate'}],
                    'label': 'Pause',
                    'method': 'animate'
                }
            ],
            'direction': 'left',
            'pad': {'r': 10, 't': 87},
            'showactive': False,
            'type': 'buttons',
            'x': 0.1,
            'xanchor': 'right',
            'y': 0,
            'yanchor': 'top'
        }],
        sliders=sliders,
        height=800,
        width=1200
    )
    
    return fig

# Fonction utilitaire pour lister tous les cyclones
def list_all_cyclones():
    """Retourne la liste de tous les cyclones disponibles"""
    return df['Nom du cyclone'].unique().tolist()

# Exemple d'utilisation
if __name__ == "__main__":
    # Afficher tous les cyclones
    print("Cyclones disponibles:", list_all_cyclones())
    
    # Visualiser tous les cyclones
    print("Génération de la carte de tous les cyclones...")
    fig_all = plot_cyclones_tracks()
    fig_all.show()
    
    # Visualiser quelques cyclones spécifiques
    print("Génération de la carte des cyclones spécifiques...")
    specific_cyclones = ['FUNDI', 'IDAI', 'KENNETH']
    fig_specific = plot_cyclones_tracks(specific_cyclones)
    fig_specific.show()
    
    # Animation pour un cyclone spécifique
    print("Génération de l'animation pour IDAI...")
    fig_animation = plot_cyclone_animation('IDAI')
    if fig_animation:
        fig_animation.show()