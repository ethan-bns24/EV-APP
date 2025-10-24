import math
import json
import time
import requests
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Tuple, Dict, Optional
import concurrent.futures
from functools import lru_cache

# ------------------------------
# App Config
# ------------------------------
st.set_page_config(page_title="EV Eco-Speed Advisory App", layout="wide")

st.title("🚗🔋 EV Eco‑Speed Advisory App — Prototype")
st.caption("Prototype Streamlit – recommande une vitesse de croisière éco pour un itinéraire donné (respect des limites à configurer).")

# ------------------------------
# Vehicle Profiles
# ------------------------------
VEHICLE_PROFILES = {
    "Tesla Model 3": {
        "mass_kg": 1850, "cda": 0.58, "crr": 0.008, "eta_drive": 0.95, 
        "regen_eff": 0.85, "aux_power_kw": 2.0, "battery_kwh": 75
    },
    "Tesla Model Y": {
        "mass_kg": 2000, "cda": 0.62, "crr": 0.008, "eta_drive": 0.95, 
        "regen_eff": 0.85, "aux_power_kw": 2.2, "battery_kwh": 75
    },
    "Audi Q4 e-tron": {
        "mass_kg": 2100, "cda": 0.70, "crr": 0.009, "eta_drive": 0.92, 
        "regen_eff": 0.80, "aux_power_kw": 2.5, "battery_kwh": 82
    },
    "BMW iX3": {
        "mass_kg": 2180, "cda": 0.68, "crr": 0.009, "eta_drive": 0.93, 
        "regen_eff": 0.82, "aux_power_kw": 2.3, "battery_kwh": 80
    },
    "Mercedes EQC": {
        "mass_kg": 2425, "cda": 0.72, "crr": 0.010, "eta_drive": 0.91, 
        "regen_eff": 0.78, "aux_power_kw": 2.8, "battery_kwh": 80
    },
    "Volkswagen ID.4": {
        "mass_kg": 2120, "cda": 0.66, "crr": 0.009, "eta_drive": 0.90, 
        "regen_eff": 0.75, "aux_power_kw": 2.0, "battery_kwh": 77
    },
    "Renault Zoe": {
        "mass_kg": 1500, "cda": 0.65, "crr": 0.010, "eta_drive": 0.90, 
        "regen_eff": 0.70, "aux_power_kw": 1.5, "battery_kwh": 52
    },
    "BMW i3": {
        "mass_kg": 1200, "cda": 0.50, "crr": 0.008, "eta_drive": 0.92, 
        "regen_eff": 0.80, "aux_power_kw": 1.8, "battery_kwh": 42
    },
    "Nissan Leaf": {
        "mass_kg": 1600, "cda": 0.68, "crr": 0.010, "eta_drive": 0.88, 
        "regen_eff": 0.75, "aux_power_kw": 1.7, "battery_kwh": 40
    },
    "Hyundai IONIQ 5": {
        "mass_kg": 1950, "cda": 0.64, "crr": 0.008, "eta_drive": 0.94, 
        "regen_eff": 0.83, "aux_power_kw": 2.1, "battery_kwh": 73
    },
    "Kia EV6": {
        "mass_kg": 1980, "cda": 0.63, "crr": 0.008, "eta_drive": 0.94, 
        "regen_eff": 0.83, "aux_power_kw": 2.1, "battery_kwh": 77
    },
    "Personnalisé": {
        "mass_kg": 1900, "cda": 0.62, "crr": 0.010, "eta_drive": 0.90, 
        "regen_eff": 0.60, "aux_power_kw": 2.0, "battery_kwh": 60
    }
}

# ------------------------------
# Sidebar – Parameters
# ------------------------------
with st.sidebar:
    st.header("⚙️ Paramètres")
    ors_key = st.text_input("OpenRouteService API Key", type="password", help="Créez une clé gratuite sur openrouteservice.org et collez-la ici.")
    st.markdown("---")
    
    # Profil véhicule
    st.subheader("🚗 Profil véhicule")
    vehicle_profile = st.selectbox("Modèle", list(VEHICLE_PROFILES.keys()))
    
    if vehicle_profile != "Personnalisé":
        profile = VEHICLE_PROFILES[vehicle_profile]
        st.info(f"Profil {vehicle_profile} chargé")
        st.caption(f"Batterie: {profile['battery_kwh']} kWh | Auxiliaires: {profile['aux_power_kw']} kW")

    st.markdown("---")
    st.subheader("Paramètres véhicule")
    
    # Utiliser les valeurs du profil ou permettre la personnalisation
    if vehicle_profile != "Personnalisé":
        profile = VEHICLE_PROFILES[vehicle_profile]
        mass_kg = st.number_input("Masse (kg)", 1000, 3500, profile["mass_kg"], 50, disabled=True)
        cda = st.number_input("Surface frontale × Cx (CdA en m²)", 0.3, 1.2, profile["cda"], 0.01, disabled=True)
        crr = st.number_input("Coefficient de roulement (Crr)", 0.005, 0.02, profile["crr"], 0.001, format="%.3f", disabled=True)
        eta_drive = st.slider("Rendement chaîne de traction (η)", 0.70, 0.98, profile["eta_drive"], 0.01, disabled=True)
        regen_eff = st.slider("Efficacité régénération (%)", 0, 90, int(profile["regen_eff"]*100), 5, disabled=True) / 100.0
        aux_power_kw = st.number_input("Puissance auxiliaire (kW)", 0.0, 5.0, profile["aux_power_kw"], 0.1, disabled=True)
        battery_kwh = st.number_input("Capacité batterie (kWh)", 20, 150, profile["battery_kwh"], 5, disabled=True)
    else:
        mass_kg = st.number_input("Masse (kg)", 1000, 3500, 1900, 50)
        cda = st.number_input("Surface frontale × Cx (CdA en m²)", 0.3, 1.2, 0.62, 0.01)
        crr = st.number_input("Coefficient de roulement (Crr)", 0.005, 0.02, 0.010, 0.001, format="%.3f")
        eta_drive = st.slider("Rendement chaîne de traction (η)", 0.70, 0.98, 0.90, 0.01)
        regen_eff = st.slider("Efficacité régénération (%)", 0, 90, 60, 5) / 100.0
        aux_power_kw = st.number_input("Puissance auxiliaire (kW)", 0.0, 5.0, 2.0, 0.1)
        battery_kwh = st.number_input("Capacité batterie (kWh)", 20, 150, 60, 5)

    rho_air = st.number_input("Densité air (kg/m³)", 0.9, 1.5, 1.225, 0.01)
    st.markdown("---")
    st.subheader("Vitesses candidates (km/h)")
    default_speeds = [80, 90, 100, 110, 120, 130]
    speeds_str = st.text_input("Liste séparée par des virgules", ", ".join(map(str, default_speeds)))
    try:
        candidate_speeds = sorted({int(s.strip()) for s in speeds_str.split(",") if s.strip()})
    except Exception:
        candidate_speeds = default_speeds
    user_speed_limit = st.number_input("Limite max sur le trajet (km/h)", 50, 130, 110, 10, help="Pour rester réaliste si l'API ne renvoie pas la limite.")
    st.markdown("---")
    st.subheader("Contraintes / Critères")
    max_time_penalty_pct = st.slider("Allongement de temps max vs vitesse la plus rapide (%)", 0, 50, 15, 1)
    minimize_target = st.selectbox("Critère", ["Minimiser l'énergie sous contrainte temps", "Score pondéré (E + λ·T)"])
    lam = st.slider("λ (pondération du temps) [pour Score pondéré]", 0.0, 10.0, 2.0, 0.5)
    
    st.markdown("---")
    st.subheader("Options avancées")
    use_elevation = st.checkbox("Utiliser les données d'élévation", value=True, help="Désactivez si vous avez des erreurs d'API")
    use_detailed_route = st.checkbox("Itinéraire détaillé", value=True, help="Désactivez pour les petits trajets")

# ------------------------------
# Helpers – Physics & Energy
# ------------------------------
g = 9.81

def seg_energy_and_time(distance_m, slope, speed_kmh, mass_kg, cda, crr, rho_air, eta_drive, regen_eff, aux_power_kw=0, **kwargs):
    """
    distance_m : segment length in meters
    slope      : dh/dx (rise over run). Positive uphill.
    speed_kmh  : vehicle speed (km/h), assumed constant over the segment
    aux_power_kw : puissance auxiliaire (climatisation, chauffage, etc.)
    returns    : (energy_Wh, time_hours)
    """
    # Validation des entrées
    if distance_m <= 0 or speed_kmh <= 0:
        return 0.0, 0.0
    
    # Limiter la pente à des valeurs réalistes
    slope = max(-0.5, min(0.5, slope))  # -50% à +50% max
    
    v = max(speed_kmh, 1e-3) * (1000/3600)  # m/s
    
    # Aerodynamic drag power
    F_aero = 0.5 * rho_air * cda * v * v
    
    # Rolling resistance (avec correction pour les pentes importantes)
    F_roll = crr * mass_kg * g * math.cos(math.atan(slope))
    
    # Grade (gravity) - avec limitation pour éviter les valeurs aberrantes
    F_grade = mass_kg * g * math.sin(math.atan(slope))

    # Tractive power (at wheels)
    P_wheels = (F_aero + F_roll + F_grade) * v  # Watts

    # Bilan électrique avec gestion de la régénération
    if P_wheels >= 0:
        P_elec = P_wheels / max(eta_drive, 1e-6)
    else:
        # Régénération limitée par l'efficacité
        P_elec = P_wheels * regen_eff

    # Ajouter la consommation auxiliaire (toujours positive)
    P_aux = aux_power_kw * 1000  # Convertir kW en W
    P_total = P_elec + P_aux

    # Time on the segment
    t = distance_m / max(v, 1e-6)  # seconds

    # Energy (Wh) = Power (W) * time (h)
    E_Wh = P_total * (t / 3600.0)
    return E_Wh, t / 3600.0

def route_energy_time(coords, elevations, speed_kmh, **veh):
    """
    coords: list of [lon, lat]
    elevations: list of elevations in meters (same length)
    returns total (energy_Wh, time_h, dist_km)
    """
    total_E = 0.0
    total_T = 0.0
    total_D = 0.0

    for i in range(1, len(coords)):
        # Gérer les coordonnées avec ou sans élévation
        if len(coords[i-1]) >= 2:
            lon1, lat1 = coords[i-1][0], coords[i-1][1]
        else:
            continue
            
        if len(coords[i]) >= 2:
            lon2, lat2 = coords[i][0], coords[i][1]
        else:
            continue
        # Haversine distance
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c  # meters
        if d < 1e-2:
            continue

        h1 = elevations[i-1]
        h2 = elevations[i]
        slope = (h2 - h1) / max(d, 1e-6)  # rise over run

        Eseg, Tseg = seg_energy_and_time(d, slope, speed_kmh, **veh)
        total_E += Eseg
        total_T += Tseg
        total_D += d

    return total_E, total_T, total_D / 1000.0

# ------------------------------
# OpenRouteService API wrappers
# ------------------------------
def ors_geocode(text, api_key):
    url = "https://api.openrouteservice.org/geocode/search"
    params = {"api_key": api_key, "text": text, "size": 1}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    feats = data.get("features", [])
    if not feats:
        return None
    lon, lat = feats[0]["geometry"]["coordinates"]
    return [lon, lat]

def ors_route(start_lonlat, end_lonlat, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json; charset=utf-8"}
    body = {
        "coordinates": [start_lonlat, end_lonlat],
        "elevation": True,  # ask elevation if available
        "instructions": False
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    data = r.json()
    
    # Extract geometry with better error handling
    try:
        # Nouveau format: routes au lieu de features
        if "routes" not in data or not data["routes"]:
            raise ValueError("Aucune route trouvée dans la réponse")
        
        route = data["routes"][0]
        
        # Le nouveau format utilise une géométrie encodée (polyline)
        # On va décoder la polyline pour obtenir les coordonnées
        try:
            import polyline
            geometry_encoded = route.get("geometry", "")
            if geometry_encoded:
                coords = polyline.decode(geometry_encoded)
                # Ajouter l'élévation si disponible
                if "bbox" in data and len(data["bbox"]) >= 6:
                    # Le bbox contient [min_lon, min_lat, min_elev, max_lon, max_lat, max_elev]
                    # On va utiliser l'élévation moyenne pour simplifier
                    avg_elevation = (data["bbox"][2] + data["bbox"][5]) / 2
                    coords = [[lon, lat, avg_elevation] for lon, lat in coords]
                else:
                    coords = [[lon, lat, 0] for lon, lat in coords]
            else:
                coords = []
        except Exception as polyline_error:
            st.warning(f"Erreur lors du décodage de la polyline: {polyline_error}")
            # Fallback: utiliser les coordonnées de départ et d'arrivée
            coords = [start_lonlat, end_lonlat]
            st.info("Utilisation des coordonnées de départ et d'arrivée uniquement")
            
            # Pour les petits trajets, essayer une approche alternative
            try:
                # Calculer la distance directe
                from math import radians, cos, sin, asin, sqrt
                def haversine_distance(lon1, lat1, lon2, lat2):
                    R = 6371000  # Rayon de la Terre en mètres
                    dlat = radians(lat2 - lat1)
                    dlon = radians(lon2 - lon1)
                    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    return R * c
                
                distance_km = haversine_distance(start_lonlat[0], start_lonlat[1], end_lonlat[0], end_lonlat[1]) / 1000
                if distance_km < 50:  # Petit trajet
                    st.info(f"Trajet court détecté ({distance_km:.1f} km) - Calculs optimisés")
            except:
                pass
        
        # Extract summary with safe access
        summary = route.get("summary", {})
        length_m = summary.get("distance", 0)
        duration_s = summary.get("duration", 0)
        
        return coords, length_m, duration_s
        
    except (KeyError, IndexError, ValueError) as e:
        st.error(f"Erreur lors de l'extraction des données de l'itinéraire: {e}")
        st.error(f"Réponse API: {json.dumps(data, indent=2)}")
        return [], 0, 0

def ors_elevation_along(coords, api_key):
    # If directions include z as third coordinate, extract it directly.
    if coords and len(coords[0]) == 3:
        return [c[2] for c in coords]

    # Otherwise, query elevation/line
    url = "https://api.openrouteservice.org/elevation/line"
    headers = {"Authorization": api_key, "Content-Type": "application/json; charset=utf-8"}
    body = {
        "format_in": "polyline",
        "format_out": "json",
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        }
    }
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    data = r.json()
    elev = [pt[2] for pt in data["geometry"]["coordinates"]]
    return elev

# ------------------------------
# Trajets typiques prédéfinis
# ------------------------------
TYPICAL_ROUTES = {
    "Paris → Lyon": ("Paris, France", "Lyon, France"),
    "Paris → Marseille": ("Paris, France", "Marseille, France"),
    "Paris → Toulouse": ("Paris, France", "Toulouse, France"),
    "Paris → Nantes": ("Paris, France", "Nantes, France"),
    "Lyon → Marseille": ("Lyon, France", "Marseille, France"),
    "Personnalisé": ("", "")
}

# ------------------------------
# Main UI
# ------------------------------
st.markdown("### 1) Saisir votre trajet")

# Sélection du trajet
route_choice = st.selectbox("Choisir un trajet typique", list(TYPICAL_ROUTES.keys()))

if route_choice != "Personnalisé":
    orig_text, dest_text = TYPICAL_ROUTES[route_choice]
    st.info(f"Trajet sélectionné: {route_choice}")
else:
    orig_text = ""
    dest_text = ""

col1, col2 = st.columns(2)
with col1:
    orig_text = st.text_input("Origine (adresse ou ville)", orig_text)
with col2:
    dest_text = st.text_input("Destination (adresse ou ville)", dest_text)

run_btn = st.button("Calculer la vitesse conseillée")

if run_btn:
    if not ors_key:
        st.error("Veuillez saisir une clé API OpenRouteService dans le panneau latéral.")
        st.stop()

    with st.spinner("Géocodage des adresses..."):
        start = ors_geocode(orig_text, ors_key)
        end = ors_geocode(dest_text, ors_key)
        if not start or not end:
            st.error("Géocodage impossible. Essayez des adresses plus précises.")
            st.stop()

    with st.spinner("Calcul d'itinéraire..."):
        try:
            coords, length_m, duration_s = ors_route(start, end, ors_key)
            if not coords or len(coords) < 2:
                st.error("Aucun itinéraire trouvé.")
                st.stop()
        except Exception as e:
            st.error(f"Erreur lors du calcul d'itinéraire: {e}")
            st.stop()

    with st.spinner("Récupération du profil altimétrique..."):
        if not use_elevation:
            st.info("Élévation désactivée - Utilisation d'altitude constante")
            elevations = [0.0 for _ in coords]
        else:
            try:
                # Pour les petits trajets, essayer une approche simplifiée
                if len(coords) <= 2:
                    st.info("Trajet court - Utilisation d'élévation constante pour simplifier")
                    elevations = [0.0 for _ in coords]
                else:
                    elevations = ors_elevation_along(coords, ors_key)
                    # Validation que les élévations ont la même longueur que les coordonnées
                    if len(elevations) != len(coords):
                        st.warning(f"Longueur des élévations ({len(elevations)}) différente des coordonnées ({len(coords)}). Utilisation d'élévation constante.")
                        elevations = [0.0 for _ in coords]
            except Exception as e:
                st.warning(f"Élévation non disponible ({e}). On supposera altitude constante.")
                elevations = [0.0 for _ in coords]

    # Validation finale des données
    if len(coords) < 2:
        st.error("Itinéraire invalide: moins de 2 points")
        st.stop()
    
    # Si on n'a que 2 points (départ/arrivée), créer un itinéraire simplifié
    if len(coords) == 2:
        st.warning("⚠️ Itinéraire simplifié: seulement 2 points (départ/arrivée)")
        st.info("Les calculs seront basés sur une ligne droite. Pour plus de précision, essayez des villes plus proches.")
        
        # Créer des points intermédiaires pour un calcul plus réaliste
        import numpy as np
        start_lon, start_lat = coords[0][0], coords[0][1]
        end_lon, end_lat = coords[1][0], coords[1][1]
        
        # Interpoler 10 points entre départ et arrivée
        n_points = 10
        lons = np.linspace(start_lon, end_lon, n_points)
        lats = np.linspace(start_lat, end_lat, n_points)
        
        coords = [[lon, lat, 0] for lon, lat in zip(lons, lats)]
        elevations = [0.0] * len(coords)
    
    if len(elevations) != len(coords):
        st.error("Données incohérentes: nombre d'élévations différent du nombre de coordonnées")
        st.stop()

    st.success("Itinéraire et altitudes récupérés ✅")

    # Vehicle params dict avec validation
    try:
        veh = dict(
            mass_kg=float(mass_kg),
            cda=float(cda),
            crr=float(crr),
            rho_air=float(rho_air),
            eta_drive=float(eta_drive),
            regen_eff=float(regen_eff),
            aux_power_kw=float(aux_power_kw),
            battery_kwh=float(battery_kwh)
        )
        
        # Validation des paramètres
        if veh['mass_kg'] <= 0 or veh['eta_drive'] <= 0 or veh['eta_drive'] > 1:
            st.error("Paramètres véhicule invalides")
            st.stop()
            
    except (ValueError, TypeError) as e:
        st.error(f"Erreur dans les paramètres véhicule: {e}")
        st.stop()

    # Limit candidate speeds by user_speed_limit
    candidates = [v for v in candidate_speeds if v <= user_speed_limit]
    if not candidates:
        candidates = [user_speed_limit]

    # Evaluate avec barre de progression
    results = []
    fastest_t = None
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, v in enumerate(candidates):
        status_text.text(f"Calcul pour {v} km/h...")
        progress_bar.progress((i + 1) / len(candidates))
        
        try:
            E_Wh, T_h, D_km = route_energy_time(coords, elevations, v, **veh)
            results.append(dict(speed=v, energy_Wh=E_Wh, time_h=T_h, dist_km=D_km))
            if fastest_t is None or T_h < fastest_t:
                fastest_t = T_h
        except Exception as e:
            st.warning(f"Erreur pour {v} km/h: {e}")
            continue
    
    progress_bar.empty()
    status_text.empty()

    # Apply selection rule
    # 1) Feasible set under time penalty constraint
    if fastest_t is not None:
        max_time_h = fastest_t * (1 + max_time_penalty_pct/100.0)
        feasible = [r for r in results if r["time_h"] <= max_time_h]
        if not feasible:
            feasible = results[:]  # fallback
    else:
        feasible = results[:]  # fallback si pas de temps de référence

    if not feasible:
        st.error("Aucun résultat valide trouvé")
        st.stop()
    
    if minimize_target == "Minimiser l'énergie sous contrainte temps":
        best = min(feasible, key=lambda r: r["energy_Wh"])
    else:
        # Normalize energy and time for a simple E + λT scoring
        E_min, E_max = min(r["energy_Wh"] for r in feasible), max(r["energy_Wh"] for r in feasible)
        T_min, T_max = min(r["time_h"] for r in feasible), max(r["time_h"] for r in feasible)
        def norm(x, a, b): return 0.0 if a==b else (x-a)/(b-a)
        best = min(
            feasible,
            key=lambda r: norm(r["energy_Wh"], E_min, E_max) + lam * norm(r["time_h"], T_min, T_max)
        )

    # Baseline (fastest among candidates)
    if results:
        fastest = min(results, key=lambda r: r["time_h"])
    else:
        st.error("Aucun résultat disponible")
        st.stop()

    # ------------------------------
    # Output metrics
    # ------------------------------
    st.markdown("### 2) Résultats")
    
    # Coût énergétique
    energy_cost_per_kwh = st.sidebar.number_input("Coût électricité (€/kWh)", 0.10, 0.50, 0.20, 0.01)
    energy_cost = (best['energy_Wh']/1000) * energy_cost_per_kwh
    
    # Autonomie restante
    battery_remaining = veh['battery_kwh'] - (best['energy_Wh']/1000)
    autonomy_pct = (battery_remaining / veh['battery_kwh']) * 100
    
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Vitesse conseillée", f"{best['speed']} km/h")
    colB.metric("Énergie estimée", f"{best['energy_Wh']/1000:.2f} kWh")
    colC.metric("Temps de trajet", f"{best['time_h']*60:.1f} min")
    colD.metric("Distance", f"{best['dist_km']:.1f} km")
    
    # Nouvelles métriques
    colE, colF, colG, colH = st.columns(4)
    colE.metric("Coût énergétique", f"{energy_cost:.2f} €")
    colF.metric("Autonomie restante", f"{battery_remaining:.1f} kWh")
    colG.metric("Niveau batterie", f"{autonomy_pct:.1f}%")
    colH.metric("Consommation", f"{best['energy_Wh']/best['dist_km']/1000:.2f} kWh/km")
    
    # Alertes pour les cas limites
    if autonomy_pct < 20:
        st.error("⚠️ Batterie faible ! Considérez recharger avant le départ.")
    elif autonomy_pct < 50:
        st.warning("🔋 Niveau de batterie modéré. Surveillez votre consommation.")
    
    if best['energy_Wh']/1000 > veh['battery_kwh']:
        st.error("❌ Consommation supérieure à la capacité batterie ! Trajet impossible.")
    elif best['energy_Wh']/1000 > veh['battery_kwh'] * 0.8:
        st.warning("⚠️ Consommation élevée. Trajet possible mais risqué.")

    # Savings vs fastest
    dE_Wh = best["energy_Wh"] - fastest["energy_Wh"]
    dT_min = (best["time_h"] - fastest["time_h"]) * 60
    st.markdown("#### Impact vs conduite la plus rapide (parmi vos vitesses candidates)")
    c1, c2 = st.columns(2)
    c1.metric("Énergie économisée", f"{-dE_Wh/1000:.2f} kWh" if dE_Wh<0 else f"+{dE_Wh/1000:.2f} kWh")
    c2.metric("Temps ajouté", f"{dT_min:.1f} min")

    # ------------------------------
    # Table results
    # ------------------------------
    st.markdown("#### Comparaison des vitesses candidates")
    import pandas as pd
    df = pd.DataFrame([
        dict(
            Vitesse_kmh=r["speed"],
            Energie_kWh=r["energy_Wh"]/1000.0,
            Temps_min=r["time_h"]*60.0
        ) for r in results
    ]).sort_values("Vitesse_kmh")
    st.dataframe(df, use_container_width=True)

    # ------------------------------
    # Plot Energy vs Speed
    # ------------------------------
    fig = plt.figure()
    plt.plot(df["Vitesse_kmh"], df["Energie_kWh"], marker="o")
    plt.xlabel("Vitesse (km/h)")
    plt.ylabel("Énergie (kWh)")
    plt.title("Consommation estimée vs vitesse")
    st.pyplot(fig)

    # ------------------------------
    # Show raw map points (simple preview)
    # ------------------------------
    st.markdown("#### Aperçu brut des points de l'itinéraire")
    st.caption("Pour une carte interactive, on pourrait ajouter folium + streamlit-folium (optionnel).")
    st.json({"n_points": len(coords), "first_points": coords[:3]})

    st.info("Astuce : Ajustez la 'Limite max' et la 'contrainte d'allongement de temps' dans la barre latérale pour voir l'effet sur la recommandation.")

else:
    st.info("Entrez une origine et une destination, fournissez votre clé ORS, puis cliquez sur *Calculer la vitesse conseillée*.")