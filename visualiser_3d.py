#!/usr/bin/env python3
"""
Script complet pour lire 'COORDONNEES.xlsx', nettoyer les données,
et produire une visualisation interactive (HTML) d'un globe avec les trajectoires
des cyclones et des marqueurs temporels (hover = date/heure).
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path


# --------------------------
# CONFIG
# --------------------------
EXCEL_PATH = Path("COORDONNEES.xlsx")  
OUTPUT_HTML = Path("cyclone_tracks_globe.html")
OUTPUT_PNG = Path("cyclone_tracks_globe.png")    
ANIMATE = True


# --------------------------
# CHARGEMENT ET NETTOYAGE
# --------------------------
def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")

    df.rename(columns=lambda c: c.strip() if isinstance(c, str) else c, inplace=True)

    expected = ['Saison cyclonique', 'Nom du cyclone', 'Durée de vie', 'Date', 'Heure', 'Lat', 'Lon']
    for c in expected:
        if c not in df.columns:
            raise RuntimeError(f"Colonne attendue manquante dans le fichier Excel : {c}")

    # supprimer lignes sans coordonnées
    df = df.loc[ df['Lat'].notna() & df['Lon'].notna() ].copy()

    df[['Saison cyclonique','Nom du cyclone','Durée de vie','Date']] = df[['Saison cyclonique','Nom du cyclone','Durée de vie','Date']].ffill()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Heure'] = df['Heure'].astype(str).str.extract(r'(\d{1,2})')[0].astype(float).fillna(0).astype(int)
    df['datetime'] = df['Date'] + pd.to_timedelta(df['Heure'], unit='h')
    df.sort_values(['Saison cyclonique','Nom du cyclone','datetime'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df

# --------------------------
# Création plotly traces et frames
# --------------------------
def make_plot(df: pd.DataFrame, animate: bool=True):
    cyclones = df['Nom du cyclone'].unique()
    seasons = df['Saison cyclonique'].unique()

    colors = px.colors.qualitative.Plotly
    color_map = {name: colors[i % len(colors)] for i, name in enumerate(cyclones)}

    fig = go.Figure()

    # Ajout chemins (lines) pour chaque cyclone
    for name in cyclones:
        sub = df[df['Nom du cyclone'] == name]
        fig.add_trace(go.Scattergeo(
            lon = sub['Lon'],
            lat = sub['Lat'],
            mode = 'lines+markers',
            line = dict(width=2),
            marker = dict(size=4),
            name = f"{name}  ({sub['Saison cyclonique'].iat[0]})",
            hoverinfo='text',
            hovertext = sub.apply(lambda r: f"{r['Nom du cyclone']}<br>{r['datetime']:%Y-%m-%d %H:%M}<br>Lat {r['Lat']:.2f}, Lon {r['Lon']:.2f}", axis=1),
            marker_color = color_map[name],
            line_color = color_map[name],
            opacity=0.9
        ))

    # Animated current positions
    if animate:
        times = sorted(df['datetime'].dropna().unique())
        frames = []
        for t in times:
            frame_df = df[df['datetime'] == t]
            frames.append(go.Frame(
                data=[
                    go.Scattergeo(
                        lon = frame_df['Lon'],
                        lat = frame_df['Lat'],
                        mode = 'markers',
                        marker = dict(size=10, symbol='circle'),
                        hoverinfo='text',
                        hovertext = frame_df.apply(lambda r: f"{r['Nom du cyclone']}<br>{r['datetime']:%Y-%m-%d %H:%M}<br>{r['Saison cyclonique']}", axis=1),
                        marker_color = [color_map[n] for n in frame_df['Nom du cyclone']]
                    )
                ],
                name = str(t) 
            ))
        fig.frames = frames

        fig.add_trace(go.Scattergeo(
            lon = [], lat = [],
            mode = 'markers',
            marker = dict(size=10),
            name = 'Positions (anim)'
        ))

    fig.update_layout(
        title_text = "Trajectoires de cyclones sur globe (interactif). Hover pour détails. ",
        showlegend = True,
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.01),
        geo = dict(
            projection_type = 'orthographic',
            showland = True,
            landcolor = "rgb(243,243,243)",
            oceancolor = "rgb(204, 224, 255)",
            showcountries = True,
            lataxis=dict(showgrid=True, dtick=30),
            lonaxis=dict(showgrid=True, dtick=60),
            coastlinewidth=0.5,
            projection_rotation = dict(lon=0, lat=0, roll=0)
        ),
        margin={"r":0,"t":40,"l":0,"b":0}
    )

    # Animation controls
    if animate and len(fig.frames) > 0:
        fig.update_layout(
            updatemenus=[{
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [None, {"frame": {"duration": 300, "redraw": True},
                                        "fromcurrent": True, "transition": {"duration": 0}}],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                           "mode": "immediate", "transition": {"duration": 0}}],
                    }
                ],
                "x": 0.02, "y": 0.05
            }]
        )
        # slider
        sliders = [{
            "steps": [
                {"args": [[frame.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                 "label": pd.to_datetime(frame.name).strftime("%Y-%m-%d %H:%M"),
                 "method": "animate"} for frame in fig.frames
            ],
            "transition": {"duration": 0},
            "x": 0.1, "y": 0,
            "currentvalue": {"font": {"size": 12}, "prefix": "Temps: ", "visible": True, "xanchor": "center"}
        }]
        fig.update_layout(sliders=sliders)

    return fig


# --------------------------
# MAIN
# --------------------------
def main():
    print("Lecture du fichier :", EXCEL_PATH)
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable: {EXCEL_PATH}")

    df = load_and_clean(EXCEL_PATH)
    print("Observations après nettoyage :", len(df))
    print(df[['Saison cyclonique','Nom du cyclone','datetime','Lat','Lon']].head())

    fig = make_plot(df, animate=ANIMATE)

    # sauvegarder HTML interactif
    fig.write_html(OUTPUT_HTML, include_plotlyjs='cdn')
    print(f"Visualisation sauvegardée dans {OUTPUT_HTML.resolve()}")

    try:
        fig.write_image(str(OUTPUT_PNG))
        print(f"PNG également sauvegardé dans {OUTPUT_PNG.resolve()}")
    except Exception as e:
        print("Export PNG échoué (kaleido peut manquer). Ignoré. Erreur:", e)
        print("Pour sauvegarder en PNG installe 'kaleido' : pip install -U kaleido")

if __name__ == "__main__":
    main()
