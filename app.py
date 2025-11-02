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
st.set_page_config(page_title="EV Eco-Speed Advisory App", layout="wide", page_icon="🚗")

# Ajouter des styles CSS personnalisés améliorés (design sobre et professionnel)
st.markdown("""
<style>
    /* Fond sobre et moderne */
    .stApp {
        background: #f5f7fa !important;
        background-attachment: fixed;
    }
    
    /* Overlay pour le contenu principal */
    .main .block-container {
        background: #ffffff !important;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        margin-top: 1rem;
        margin-bottom: 2rem;
        border: 1px solid #e1e8ed;
    }
    
    /* Métriques améliorées - design sobre */
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricDelta"] {
        color: inherit !important;
    }
    
    [data-testid="stMetricContainer"] {
        background: #ffffff !important;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e1e8ed;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
    }
    
    [data-testid="stMetricContainer"]:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    
    /* Messages d'information */
    [data-testid="stAlert"] {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Boutons améliorés - design sobre */
    .stButton > button {
        background: #2c3e50 !important;
        color: white !important;
        font-weight: 600;
        border: none !important;
        border-radius: 8px;
        padding: 0.7rem 2rem;
        transition: all 0.3s;
        box-shadow: 0 2px 8px rgba(44, 62, 80, 0.2);
    }
    
    .stButton > button:hover {
        background: #34495e !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(44, 62, 80, 0.3);
    }
    
    /* Logo container - design sobre */
    .logo-container {
        text-align: center;
        margin-bottom: 2rem;
        padding: 2rem;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e1e8ed;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    
    .logo-emoji {
        font-size: 4rem;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .logo-container h1 {
        color: #2c3e50;
        font-weight: 700;
    }
    
    .logo-container p {
        color: #7f8c8d;
    }
    
    /* Séparateurs stylisés - sobre */
    hr {
        border: none;
        height: 1px;
        background: #e1e8ed;
        margin: 2rem 0;
    }
    
    /* Titres améliorés */
    h1, h2, h3 {
        color: #2c3e50;
    }
    
    /* Sidebar améliorée */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e1e8ed;
    }
    
    /* Scrollbar personnalisée - sobre */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #bdc3c7;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #95a5a6;
    }
    
    /* Tables améliorées */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Logo et header personnalisé
st.markdown("""
<div class="logo-container">
    <span class="logo-emoji">🚗🔋⚡</span>
    <h1 style="margin: 0; color: #2c3e50;">Optimiseur de Vitesse pour Véhicules Électriques</h1>
    <p style="margin-top: 0.5rem; color: #7f8c8d; font-size: 1.1rem;">
        Planifiez vos trajets intelligemment en optimisant votre consommation énergétique
    </p>
</div>
""", unsafe_allow_html=True)

# Ajouter des informations sur les nouvelles fonctionnalités
with st.expander("ℹ️ Nouveautés et fonctionnalités", expanded=False):
    st.markdown("""
        **✨ Améliorations récentes :**
        - 👥 Prise en compte du **nombre de passagers et de leur poids**
        - 🌡️ Paramétrage de la **climatisation** pour des calculs précis
        - 🔋 **Planification des recharges** : pourcentages de batterie au départ et à l'arrivée
        - 📊 **Graphiques améliorés** avec visualisation des données optimisées
        - 🚦 **Nouveau : Limitations de vitesse par segment** : prise en compte automatique des limitations selon le type de route (autoroute 130 km/h, route nationale 90 km/h, ville 50 km/h, etc.)
        - 🛣️ **Détection améliorée des carrefours** : identification précise des intersections, ronds-points et points de ralentissement
        
        Cet outil vous aide à :
        - Maximiser l'autonomie de votre véhicule électrique
        - Réduire vos coûts énergétiques
        - Planifier vos arrêts de recharge
        - Obtenir des estimations de consommation plus réalistes avec des vitesses adaptées aux limitations réelles
        """)

st.markdown("---")

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
    # Logo dans la sidebar
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🚗⚡</div>
        <div style="font-weight: 600; color: #667eea; font-size: 1.1rem;">EV Optimizer</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.header("⚙️ Paramètres")
    
    # Aide rapide
    with st.expander("💡 Astuce", expanded=False):
        st.markdown("""
        **Les facteurs qui influencent votre consommation :**
        - 🧍 **Poids** : Plus de passagers = plus de consommation
        - 🌡️ **Climatisation** : Peut augmenter de 10-30% la consommation
        - 🏔️ **Topographie** : Les montées augmentent significativement la consommation
        - 🏎️ **Vitesse** : La consommation augmente exponentiellement avec la vitesse
        - 🌡️ **Température** : Froid ou chaud extrême réduit l'efficacité de la batterie
        """)
    
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
    default_speeds = list(range(50, 131, 5))
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
    st.subheader("👥 Charge et passagers")
    num_passengers = st.number_input("Nombre de passagers", 0, 7, 1, 1, help="Conducteur inclus")
    avg_weight_kg = st.number_input("Poids moyen par personne (kg)", 40, 120, 75, 5)
    total_passenger_weight = num_passengers * avg_weight_kg
    
    st.markdown("---")
    st.subheader("🌡️ Conditions de conduite")
    use_climate = st.checkbox("Utiliser la climatisation", value=False)
    if use_climate:
        climate_intensity = st.slider("Intensité de la clim/chauffage (%)", 0, 100, 50, 10)
    else:
        climate_intensity = 0
    
    st.markdown("---")
    st.subheader("🔋 État de la batterie")
    battery_start_pct = st.slider("Charge de batterie au départ (%)", 20, 100, 100, 5)
    battery_end_pct = st.slider("Charge cible à l'arrivée (%)", 5, 90, 20, 5)
    
    st.markdown("---")
    st.subheader("Options avancées")
    use_elevation = st.checkbox("Utiliser les données d'élévation", value=True, help="Désactivez si vous avez des erreurs d'API")
    use_segmented_speeds = st.checkbox("Limitations de vitesse par segment", value=True, help="Prend en compte les limitations selon le type de route (autoroute, ville, etc.)")
    if use_segmented_speeds:
        min_speed_delta = st.number_input("Delta vitesse minimum (km/h)", 0, 50, 20, 5, help="Vitesse minimum = limitation - delta (ex: autoroute 130 km/h avec delta 20 = minimum 110 km/h)")
    else:
        min_speed_delta = 0
    use_detailed_route = st.checkbox("Itinéraire détaillé", value=True, help="Désactivez pour les petits trajets")
    debug_mode = st.checkbox("Mode debug", value=False, help="Affiche des informations intermédiaires")

# ------------------------------
# Helpers – Physics & Energy
# ------------------------------
g = 9.81

def is_valid_ors_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    k = key.strip()
    if not k:
        return False
    # Heuristique: ORS renvoie généralement une clé base64-like
    # Rejeter clairement les messages d'erreur ou URLs collés par erreur
    banned_substrings = ["http", "Client Error", "Bad Request", "Forbidden", "Erreur", "Error:"]
    if any(b.lower() in k.lower() for b in banned_substrings):
        return False
    # Caractères autorisés (base64 + '=') et longueur plausible
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-.")
    if not all(c in allowed for c in k):
        return False
    return 20 <= len(k) <= 256

def calculate_charging_stops(battery_kwh, energy_needed_kwh, start_pct, end_pct):
    """
    Calcule le nombre de recharges nécessaires pour un trajet.
    
    Args:
        battery_kwh: Capacité totale de la batterie en kWh
        energy_needed_kwh: Énergie nécessaire pour le trajet
        start_pct: Pourcentage de batterie au départ
        end_pct: Pourcentage de batterie cible à l'arrivée
    
    Returns:
        dict avec: num_stops, usable_battery, energy_per_leg
    """
    # Batterie utilisable au départ
    usable_start_kwh = battery_kwh * (start_pct / 100.0)
    
    # Batterie cible à l'arrivée
    target_end_kwh = battery_kwh * (end_pct / 100.0)
    
    # Bande de manoeuvre: on garde toujours au moins 10% de sécurité
    safety_margin = battery_kwh * 0.10
    
    # Batterie réellement utilisable par "leg" (segment entre deux charges)
    usable_battery = battery_kwh - safety_margin
    
    if usable_battery <= 0:
        return {"num_stops": 999, "usable_battery": 0, "energy_per_leg": usable_battery}
    
    # Énergie disponible au départ
    energy_available = usable_start_kwh - max(safety_margin, target_end_kwh)
    
    # Calculer le nombre de recharges
    if energy_needed_kwh <= energy_available:
        return {"num_stops": 0, "usable_battery": usable_battery, "energy_per_leg": usable_battery}
    
    remaining_energy = energy_needed_kwh - energy_available
    num_stops = math.ceil(remaining_energy / usable_battery)
    
    return {"num_stops": max(0, num_stops), "usable_battery": usable_battery, "energy_per_leg": usable_battery}

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
    speed_kmh: vitesse constante OU list de vitesses par segment
    returns total (energy_Wh, time_h, dist_km)
    """
    total_E = 0.0
    total_T = 0.0
    total_D = 0.0
    
    # Gérer vitesse constante ou liste de vitesses
    is_speed_list = isinstance(speed_kmh, list)
    if is_speed_list and len(speed_kmh) != len(coords) - 1:
        # Si la liste n'a pas la bonne taille, utiliser la première vitesse
        speed_kmh = speed_kmh[0] if speed_kmh else 50
        is_speed_list = False

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

        # Utiliser la vitesse pour ce segment spécifique
        seg_speed = speed_kmh[i-1] if is_speed_list else speed_kmh
        
        # Appliquer ralentissement aux carrefours si nécessaire
        # (sera géré dans la fonction appelante avec slowdown_points)

        Eseg, Tseg = seg_energy_and_time(d, slope, seg_speed, **veh)
        total_E += Eseg
        total_T += Tseg
        total_D += d

    return total_E, total_T, total_D / 1000.0

# ------------------------------
# Route segmentation and speed limits
# ------------------------------
def get_speed_limit_by_road_type(road_type: str, user_max_speed: int = 130) -> int:
    """
    Retourne la limitation de vitesse typique selon le type de route.
    Args:
        road_type: Type de route depuis ORS (ex: "motorway", "trunk", "primary", etc.)
        user_max_speed: Limite maximale définie par l'utilisateur
    Returns:
        Limitation de vitesse en km/h
    """
    # Mapping des types de route ORS vers limitations de vitesse en France
    speed_mapping = {
        "motorway": min(130, user_max_speed),  # Autoroute
        "trunk": min(110, user_max_speed),     # Route express
        "primary": min(90, user_max_speed),    # Route nationale
        "secondary": min(90, user_max_speed),  # Route départementale principale
        "tertiary": min(90, user_max_speed),   # Route départementale secondaire
        "unclassified": 50,                    # Route non classée (assimilée zone urbaine)
        "residential": 50,                     # Zone résidentielle
        "service": 30,                          # Route de service
    }
    
    # Recherche par préfixe (car ORS peut retourner "motorway_link", etc.)
    for key, speed in speed_mapping.items():
        if road_type and key in road_type.lower():
            return speed
    
    # Par défaut, utiliser 50 km/h (zone urbaine)
    return 50

def detect_intersections_improved(steps, detailed_segments, coords):
    """
    Détecte les carrefours et intersections de manière améliorée.
    Returns:
        dict avec: intersections (list of indices), slowdown_points (list)
    """
    intersections = []
    slowdown_points = []
    
    if not steps:
        return {"intersections": intersections, "slowdown_points": slowdown_points}
    
    # Analyser les étapes pour détecter les intersections
    for i, step in enumerate(steps):
        instr = str(step.get("instruction", "")).lower()
        step_type = step.get("type", 0)
        distance = step.get("distance", 0)
        
        # Types de manœuvres qui indiquent des intersections/carrefours
        intersection_keywords = [
            "tournez", "tourner", "turn", "tourné", "tournant",
            "roundabout", "rond-point", "rond point", "round-about",
            "bifurquez", "bifurcation", "fork", "bifurquer",
            "u-turn", "demi-tour", "uturn",
            "merge", "mergez", "fusion",
            "jonction", "junction", "join",
            "quittez", "exit", "sortie",
            "continuez", "continue",
            "prenez", "take",
            "intersection", "croisement", "crossing"
        ]
        
        # Détecter les carrefours par mots-clés
        if any(keyword in instr for keyword in intersection_keywords):
            # Calculer l'index approximatif dans coords basé sur la distance
            intersections.append(i)
            
        # Détecter les ronds-points spécifiquement
        if "roundabout" in instr or "rond-point" in instr or "rond point" in instr:
            slowdown_points.append({"type": "roundabout", "step_index": i})
        
        # Détecter les virages serrés (angles significatifs)
        if step_type in [1, 2, 3, 4, 5, 6]:  # Types de virages dans ORS
            # Virage serré = ralentissement nécessaire
            if distance < 100:  # Court segment = virage serré
                slowdown_points.append({"type": "sharp_turn", "step_index": i})
        
        # Détecter les changements de type de route (indique souvent une intersection)
        if i > 0 and detailed_segments:
            # Si on change de segment, c'est souvent une intersection
            pass
    
    return {"intersections": intersections, "slowdown_points": slowdown_points}

def create_segmented_speeds(coords, steps, detailed_segments, candidate_speed: int, user_max_speed: int, min_speed_delta: int = 20):
    """
    Crée une liste de vitesses segmentées basée sur les types de route.
    Si les types de route ne sont pas disponibles, utilise la vitesse candidate partout.
    Args:
        min_speed_delta: Delta minimum sous la limitation (ex: 20 km/h signifie qu'on peut rouler à limitation - 20 km/h minimum)
    Returns:
        list of speeds (km/h) pour chaque segment entre coords
    """
    # Si pas de données détaillées, utiliser la vitesse candidate partout (fallback simple)
    if not steps or not detailed_segments:
        return [candidate_speed] * (len(coords) - 1)
    
    segmented_speeds = []
    
    # Calculer la distance totale pour mapper proportionnellement
    total_route_distance = sum(seg.get("distance", 0) for seg in detailed_segments) or 1
    
    # Créer un mapping des segments avec leurs distances cumulées
    segment_boundaries = []
    cumul_dist = 0
    for seg in detailed_segments:
        seg_dist = seg.get("distance", 0)
        segment_boundaries.append({
            "start": cumul_dist,
            "end": cumul_dist + seg_dist,
            "segment": seg
        })
        cumul_dist += seg_dist
    
    # Calculer la distance cumulée pour chaque point de coordonnées
    cumul_coord_dist = 0
    coord_distances = [0]
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][0], coords[i][1]
        lon2, lat2 = coords[i+1][0], coords[i+1][1]
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        segment_distance = R * c
        cumul_coord_dist += segment_distance
        coord_distances.append(cumul_coord_dist)
    
    # Normaliser les distances pour le mapping
    if coord_distances[-1] > 0:
        coord_ratio = total_route_distance / coord_distances[-1]
        coord_distances = [d * coord_ratio for d in coord_distances]
    
    # Assigner une vitesse à chaque segment de coordonnées
    # Flag pour vérifier si on a trouvé des types de route valides
    found_road_types = False
    
    for i in range(len(coords) - 1):
        # Trouver dans quel segment ORS se trouve ce point
        mid_dist = (coord_distances[i] + coord_distances[i+1]) / 2
        
        segment_found = None
        for seg_bound in segment_boundaries:
            if seg_bound["start"] <= mid_dist < seg_bound["end"]:
                segment_found = seg_bound["segment"]
                break
        
        if segment_found:
            steps_in_seg = segment_found.get("steps", [])
            way_type = None
            road_type = None
            
            if steps_in_seg:
                # Extraire le type de route d'un step du segment
                first_step = steps_in_seg[0]
                way_type = first_step.get("way_type", None)
                road_type = first_step.get("road_type", None)
            
            # Essayer aussi dans les propriétés du segment directement
            if not road_type and not way_type:
                way_type = segment_found.get("way_type", None)
                road_type = segment_found.get("road_type", None)
            
            # Utiliser le type de route pour déterminer la vitesse limite
            if road_type:
                speed_limit = get_speed_limit_by_road_type(str(road_type), user_max_speed)
                found_road_types = True
                # Calculer la vitesse minimum autorisée (limitation - delta)
                min_allowed_speed = max(30, speed_limit - min_speed_delta)  # Minimum absolu de 30 km/h
                # Utiliser la vitesse candidate mais :
                # - Limité par le maximum (limitation de vitesse)
                # - Limitée par le minimum (ne pas rouler trop lentement sur autoroute)
                final_speed = max(min_allowed_speed, min(candidate_speed, speed_limit))
            elif way_type:
                speed_limit = get_speed_limit_by_road_type(str(way_type), user_max_speed)
                found_road_types = True
                # Calculer la vitesse minimum autorisée (limitation - delta)
                min_allowed_speed = max(30, speed_limit - min_speed_delta)  # Minimum absolu de 30 km/h
                # Utiliser la vitesse candidate mais :
                # - Limité par le maximum (limitation de vitesse)
                # - Limitée par le minimum (ne pas rouler trop lentement sur autoroute)
                final_speed = max(min_allowed_speed, min(candidate_speed, speed_limit))
            else:
                # Si pas de type de route détecté, utiliser la vitesse candidate directement
                final_speed = candidate_speed
            
            segmented_speeds.append(final_speed)
        else:
            # Fallback: utiliser la vitesse candidate directement
            segmented_speeds.append(candidate_speed)
    
    # Si aucun type de route n'a été trouvé, utiliser la vitesse candidate partout
    # Cela garantit que les résultats varient avec la vitesse candidate testée
    if not found_road_types:
        return [candidate_speed] * (len(coords) - 1)
    
    return segmented_speeds if segmented_speeds else [candidate_speed] * (len(coords) - 1)

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

def ors_route_steps(start_lonlat, end_lonlat, api_key):
    """Récupère les étapes (instructions) ORS pour estimer les carrefours/ralentissements."""
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json; charset=utf-8"}
    body = {
        "coordinates": [start_lonlat, end_lonlat],
        "elevation": False,
        "instructions": True
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        r.raise_for_status()
        data = r.json()
        if "routes" not in data or not data["routes"]:
            return [], []
        route = data["routes"][0]
        segments = route.get("segments", [])
        steps = []
        detailed_segments = []
        for seg in segments:
            steps.extend(seg.get("steps", []))
            # Extraire les informations détaillées des segments (types de route, etc.)
            detailed_segments.append(seg)
        return steps, detailed_segments
    except Exception:
        return [], []

def ors_route(start_lonlat, end_lonlat, api_key, include_instructions=False):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json; charset=utf-8"}
    body = {
        "coordinates": [start_lonlat, end_lonlat],
        "elevation": False,  # récupérer d'abord la géométrie pure, élévation ensuite
        "instructions": include_instructions
    }
    # Demander un retour GeoJSON côté API pour éviter tout décodage polyline
    r = requests.post(url, headers=headers, params={"format": "geojson"}, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    data = r.json()
    
    # Extract geometry with better error handling
    try:
        coords = []
        length_m = 0
        duration_s = 0

        if "routes" in data and data["routes"]:
            route = data["routes"][0]
            geometry = route.get("geometry")
            if isinstance(geometry, dict) and geometry.get("type") == "LineString":
                coords = geometry.get("coordinates", [])
            elif isinstance(geometry, str) and geometry:
                try:
                    import polyline
                    decoded = polyline.decode(geometry)
                    # polyline returns [(lat, lon)], we convert to [lon, lat]
                    coords = [[lon, lat] for (lat, lon) in decoded]
                except Exception:
                    coords = []
            summary = route.get("summary", {})
            length_m = summary.get("distance", 0)
            duration_s = summary.get("duration", 0)
        elif "features" in data and data["features"]:
            feature = data["features"][0]
            geometry = feature.get("geometry", {})
            if isinstance(geometry, dict) and geometry.get("type") == "LineString":
                coords = geometry.get("coordinates", [])
            props = feature.get("properties", {})
            if isinstance(props, dict):
                segments = props.get("segments", [])
                if segments:
                    summary = segments[0].get("summary", {})
                    length_m = summary.get("distance", 0)
                    duration_s = summary.get("duration", 0)

        if not coords:
            st.warning("Géométrie non disponible, fallback sur départ/arrivée")
            coords = [start_lonlat, end_lonlat]

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
    # L'API a une limite sur le nombre de points: on sous-échantillonne à ~2000 max
    max_pts = 1000
    if len(coords) > max_pts:
        step = max(1, len(coords) // max_pts + (1 if len(coords) % max_pts else 0))
        reduced = coords[::step]
        if reduced[-1] != coords[-1]:
            reduced.append(coords[-1])
    else:
        reduced = coords
    body = {
        "format_in": "geojson",
        "format_out": "json",
        "geometry": {
            "type": "LineString",
            "coordinates": reduced
        }
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        r.raise_for_status()
        data = r.json()
        elev = [pt[2] for pt in data["geometry"]["coordinates"]]
        def _interp_back(sampled, full_len):
            if len(sampled) == full_len:
                return sampled
            import numpy as np
            x_old = np.linspace(0.0, 1.0, len(sampled))
            x_new = np.linspace(0.0, 1.0, full_len)
            return np.interp(x_new, x_old, sampled).tolist()
        if len(reduced) != len(coords):
            elev = _interp_back(elev, len(coords))
        # Si tout est à 0, tenter un fallback Open‑Elevation
        if elev and max(elev) == 0.0 and min(elev) == 0.0:
            raise ValueError("flat_zero")
        return elev
    except Exception:
        # Fallbacks: encoded polyline puis Open‑Elevation
        try:
            if len(coords) > 200:
                step = max(1, len(coords) // 200)
                reduced2 = coords[::step]
                if reduced2[-1] != coords[-1]:
                    reduced2.append(coords[-1])
            else:
                reduced2 = coords
            # 1) encoded polyline (lat,lon) attendu
            import polyline as _poly
            import numpy as _np
            latlon = [(c[1], c[0]) for c in reduced2]
            enc = _poly.encode(latlon, precision=5)
            body_poly = {"format_in": "encodedpolyline", "format_out": "json", "geometry": enc}
            r2 = requests.post(url, headers=headers, data=json.dumps(body_poly), timeout=60)
            r2.raise_for_status()
            data2 = r2.json()
            elev2 = [pt[2] for pt in data2["geometry"]["coordinates"]]
            if len(reduced2) != len(coords):
                x_old = _np.linspace(0.0, 1.0, len(reduced2))
                x_new = _np.linspace(0.0, 1.0, len(coords))
                elev2 = _np.interp(x_new, x_old, elev2).tolist()
            if elev2 and max(elev2) == 0.0 and min(elev2) == 0.0:
                raise ValueError("flat_zero_poly")
            return elev2
        except Exception:
            try:
                # 2) Open‑Elevation gratuit en lots
                import numpy as _np
                def fetch_chunk(chunk):
                    locs = "|".join(f"{lat},{lon}" for lon, lat in chunk)
                    resp = requests.get("https://api.open-elevation.com/api/v1/lookup", params={"locations": locs}, timeout=60)
                    resp.raise_for_status()
                    j = resp.json()
                    return [p.get("elevation", 0.0) for p in j.get("results", [])]
                pts = reduced2 if len(reduced2) < len(coords) else coords
                out = []
                for i in range(0, len(pts), 90):
                    out.extend(fetch_chunk(pts[i:i+90]))
                if len(pts) != len(coords):
                    x_old = _np.linspace(0.0, 1.0, len(pts))
                    x_new = _np.linspace(0.0, 1.0, len(coords))
                    out = _np.interp(x_new, x_old, out).tolist()
                return out
            except Exception:
                # 3) plat si tout échoue
                return [0.0 for _ in coords]

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
    if not ors_key or not is_valid_ors_key(ors_key):
        st.error("Clé API OpenRouteService invalide. Collez votre clé ORS (pas un message d'erreur).")
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

    if debug_mode:
        st.caption("[DEBUG] Longueurs après élévation")
        st.json({"n_coords": len(coords), "n_elev": len(elevations)})
        try:
            if elevations:
                import numpy as np
                arr = np.array(elevations, dtype=float)
                st.caption("[DEBUG] Stats élévation")
                st.json({
                    "min_m": float(np.min(arr)),
                    "max_m": float(np.max(arr)),
                    "mean_m": float(np.mean(arr)),
                    "zeros": int(np.sum(arr == 0.0)),
                })
        except Exception as _:
            pass

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

    # ------------------------------
    # Relief (pentes, dénivelés)
    # ------------------------------
    total_up_m = 0.0
    total_down_m = 0.0
    max_abs_slope_pct = 0.0
    for i in range(1, len(elevations)):
        dh = elevations[i] - elevations[i-1]
        if dh > 0:
            total_up_m += dh
        elif dh < 0:
            total_down_m += -dh
        # approx slope locale sur le segment
        # recalcul distance locale
        lon1, lat1 = coords[i-1][0], coords[i-1][1]
        lon2, lat2 = coords[i][0], coords[i][1]
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = 6371000.0 * c
        if d > 1e-3:
            slope_pct = abs((elevations[i] - elevations[i-1]) / d) * 100.0
            if slope_pct > max_abs_slope_pct:
                max_abs_slope_pct = slope_pct

    # ------------------------------
    # Carrefours / ralentissements estimés via instructions ORS (amélioré)
    # ------------------------------
    with st.spinner("Analyse des carrefours et limitations de vitesse..."):
        steps, detailed_segments = ors_route_steps(start, end, ors_key)
        intersection_data = detect_intersections_improved(steps, detailed_segments, coords)
        slowdown_count = len(intersection_data["intersections"]) + len(intersection_data["slowdown_points"])
    if debug_mode:
        st.caption("[DEBUG] Récap brut après récupération d'itinéraire")
        st.json({
            "n_coords": len(coords),
            "length_m": length_m,
            "duration_s": duration_s,
        })

    # Pas de segmentation avancée ni carte dans la version d'origine

    # (debug segments supprimé)

    # Ajuster la puissance auxiliaire en fonction de la climatisation
    climate_power_adjustment = 0
    if use_climate:
        # Ajouter de la puissance supplémentaire pour la clim (basé sur l'intensité)
        # Base: 1-3 kW pour la clim selon l'intensité
        climate_power_adjustment = (climate_intensity / 100.0) * 3.0
    
    adjusted_aux_power = aux_power_kw + climate_power_adjustment
    
    # Calculer le poids total (véhicule + passagers)
    total_mass_kg = float(mass_kg) + float(total_passenger_weight)
    
    # Vehicle params dict avec validation
    try:
        veh = dict(
            mass_kg=total_mass_kg,
            cda=float(cda),
            crr=float(crr),
            rho_air=float(rho_air),
            eta_drive=float(eta_drive),
            regen_eff=float(regen_eff),
            aux_power_kw=adjusted_aux_power,
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

    # Evaluate avec barre de progression (avec vitesses segmentées)
    results = []
    fastest_t = None
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, v in enumerate(candidates):
        status_text.text(f"Calcul pour {v} km/h (avec limitations par segment)...")
        progress_bar.progress((i + 1) / len(candidates))
        
        try:
            # Utiliser des vitesses segmentées si activé, sinon vitesse constante
            if use_segmented_speeds and steps and detailed_segments:
                # Créer des vitesses segmentées basées sur les types de route
                segmented_speeds = create_segmented_speeds(coords, steps, detailed_segments, v, user_speed_limit, min_speed_delta)
                
                # Appliquer des ralentissements aux carrefours
                if intersection_data["slowdown_points"]:
                    # Réduire la vitesse aux points de ralentissement (carrefours, ronds-points, virages)
                    for slowdown in intersection_data["slowdown_points"]:
                        step_idx = slowdown.get("step_index", 0)
                        # Estimer l'index approximatif dans les coordonnées
                        # Approximation basée sur la proportion des steps
                        if steps and len(steps) > 0:
                            coord_ratio = step_idx / max(len(steps), 1)
                            coord_idx = min(int(coord_ratio * (len(coords) - 1)), len(segmented_speeds) - 1)
                            if 0 <= coord_idx < len(segmented_speeds):
                                # Réduire la vitesse de 30% aux carrefours
                                segmented_speeds[coord_idx] = max(segmented_speeds[coord_idx] * 0.7, 30)
                
                # Utiliser les vitesses segmentées pour le calcul
                E_Wh, T_h, D_km = route_energy_time(coords, elevations, segmented_speeds, **veh)
                
                # Calculer la vitesse moyenne pour l'affichage
                avg_speed = sum(segmented_speeds) / len(segmented_speeds) if segmented_speeds else v
            else:
                # Vitesse constante (ancienne méthode)
                E_Wh, T_h, D_km = route_energy_time(coords, elevations, v, **veh)
                avg_speed = v
            
            results.append(dict(speed=v, energy_Wh=E_Wh, time_h=T_h, dist_km=D_km, avg_speed=avg_speed))
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
    
    # Calcul du nombre de recharges nécessaires
    energy_needed_kwh = best['energy_Wh'] / 1000
    charge_info = calculate_charging_stops(battery_kwh, energy_needed_kwh, battery_start_pct, battery_end_pct)
    
    # Coût énergétique
    energy_cost_per_kwh = st.sidebar.number_input("Coût électricité (€/kWh)", 0.10, 0.50, 0.20, 0.01)
    energy_cost = energy_needed_kwh * energy_cost_per_kwh
    
    # Batterie au départ et calculé pour l'arrivée
    battery_start_kwh = battery_kwh * (battery_start_pct / 100.0)
    battery_after_trip = battery_start_kwh - energy_needed_kwh
    battery_end_pct_calc = (battery_after_trip / battery_kwh) * 100
    
    # Afficher un résumé des paramètres du voyage
    with st.expander("📋 Résumé des paramètres du voyage", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 Passagers", f"{num_passengers}", help=f"Poids total: {total_passenger_weight} kg")
        col2.metric("🌡️ Climatisation", "✅ Oui" if use_climate else "❌ Non", help=f"Intensité: {climate_intensity}%" if use_climate else "")
        col3.metric("🔋 Batterie départ", f"{battery_start_pct}%", help=f"{battery_start_kwh:.1f} kWh")
        col4.metric("🎯 Batterie cible", f"{battery_end_pct}%", help=f"{battery_kwh * (battery_end_pct/100):.1f} kWh")
    
    # Afficher les informations de charge
    st.info(f"📊 **Analyse de batterie** : Charge au départ {battery_start_pct}% ({battery_start_kwh:.1f} kWh) | Après trajet: {battery_end_pct_calc:.1f}% ({battery_after_trip:.1f} kWh)")
    
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Vitesse conseillée", f"{best['speed']} km/h")
    colB.metric("Énergie estimée", f"{energy_needed_kwh:.2f} kWh")
    colC.metric("Temps de trajet", f"{best['time_h']*60:.1f} min")
    colD.metric("Distance", f"{best['dist_km']:.1f} km")

    # Bloc relief et carrefours
    colR1, colR2, colR3 = st.columns(3)
    colR1.metric("Dénivelé +", f"{total_up_m:.0f} m")
    colR2.metric("Dénivelé -", f"{total_down_m:.0f} m")
    colR3.metric("Pente max (abs)", f"{max_abs_slope_pct:.1f} %")

    st.caption("Carrefours/ralentissements détectés (analyse améliorée)")
    col_int1, col_int2 = st.columns(2)
    col_int1.metric("Carrefours/intersections", len(intersection_data["intersections"]))
    col_int2.metric("Points de ralentissement", len(intersection_data["slowdown_points"]))
    
    if use_segmented_speeds:
        st.success("✅ **Limitations de vitesse par segment activées** : Les calculs prennent en compte les limitations selon le type de route (autoroute 130 km/h, ville 50 km/h, etc.)")
        if 'avg_speed' in best:
            st.info(f"ℹ️ Vitesse moyenne réelle sur le trajet : {best['avg_speed']:.1f} km/h (vitesse conseillée de base : {best['speed']} km/h)")
    
    # Nouvelles métriques avec recharge
    colE, colF, colG, colH = st.columns(4)
    colE.metric("Coût énergétique", f"{energy_cost:.2f} €")
    colF.metric("🔌 Recharges nécessaires", f"{charge_info['num_stops']}", help="Nombre de recharges à planifier")
    colG.metric("Niveau batterie après", f"{battery_end_pct_calc:.1f}%")
    colH.metric("Consommation", f"{energy_needed_kwh/best['dist_km']:.2f} kWh/km")
    
    # Affichage du résultat des recharges
    if charge_info['num_stops'] == 0:
        st.success(f"✅ **Pas de recharge nécessaire !** Vous avez assez de batterie pour ce trajet.")
    elif charge_info['num_stops'] > 0 and charge_info['num_stops'] < 10:
        st.warning(f"🔋 **{charge_info['num_stops']} recharge(s) recommandée(s)** pour ce trajet.")
    else:
        st.error(f"⚠️ **Trajet difficile** : La consommation est très élevée ({charge_info['num_stops']} recharges estimées).")
    
    # Alertes pour les cas limites
    if battery_end_pct_calc < 20:
        st.error("⚠️ Batterie très faible à l'arrivée ! Rechargez avant de partir.")
    elif battery_end_pct_calc < 50:
        st.warning("🔋 Niveau de batterie modéré à l'arrivée. Surveillez votre consommation.")
    
    if energy_needed_kwh > veh['battery_kwh']:
        st.error("❌ Consommation supérieure à la capacité batterie ! Trajet impossible.")
    elif energy_needed_kwh > veh['battery_kwh'] * 0.8:
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
    # Plot Energy vs Speed - Graphiques améliorés
    # ------------------------------
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        fig, ax = plt.subplots(figsize=(8, 5))
        # Trouver la vitesse optimale pour la colorer différemment
        best_speed_index = df[df["Vitesse_kmh"] == best["speed"]].index[0]
        
        # Créer un array de couleurs
        colors = ['#2ecc71' if idx == best_speed_index else '#3498db' for idx in range(len(df))]
        
        ax.scatter(df["Vitesse_kmh"], df["Energie_kWh"], 
                   s=100, c=colors, alpha=0.7, edgecolors='darkblue', linewidth=2)
        ax.plot(df["Vitesse_kmh"], df["Energie_kWh"], 
                color='#95a5a6', linewidth=1, linestyle='--', alpha=0.5)
        
        # Marquer la vitesse optimale
        if best_speed_index < len(df):
            ax.scatter(best["speed"], best["energy_Wh"]/1000, 
                      s=200, c='#e74c3c', marker='*', edgecolors='darkred', 
                      linewidth=2, label=f'Recommandé: {best["speed"]} km/h', zorder=5)
        
        ax.set_xlabel("Vitesse (km/h)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Énergie (kWh)", fontsize=12, fontweight='bold')
        ax.set_title("⚡ Consommation énergétique vs Vitesse", fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.legend(fontsize=10)
        plt.tight_layout()
        st.pyplot(fig)
    
    with col_graph2:
        fig, ax = plt.subplots(figsize=(8, 5))
        # Graphique temps vs vitesse
        ax.scatter(df["Vitesse_kmh"], df["Temps_min"], 
                   s=100, c='#e67e22', alpha=0.7, edgecolors='darkorange', linewidth=2)
        ax.plot(df["Vitesse_kmh"], df["Temps_min"], 
                color='#95a5a6', linewidth=1, linestyle='--', alpha=0.5)
        
        # Marquer la vitesse optimale
        best_speed_index = df[df["Vitesse_kmh"] == best["speed"]].index[0]
        if best_speed_index < len(df):
            ax.scatter(best["speed"], best["time_h"]*60, 
                      s=200, c='#e74c3c', marker='*', edgecolors='darkred', 
                      linewidth=2, label=f'Recommandé: {best["speed"]} km/h', zorder=5)
        
        ax.set_xlabel("Vitesse (km/h)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Temps (minutes)", fontsize=12, fontweight='bold')
        ax.set_title("⏱️ Temps de trajet vs Vitesse", fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.legend(fontsize=10)
        plt.tight_layout()
        st.pyplot(fig)

    # (aucune carte interactive dans la version d'origine)

    st.info("Astuce : Ajustez la 'Limite max' et la 'contrainte d'allongement de temps' dans la barre latérale pour voir l'effet sur la recommandation.")

else:
    st.info("Entrez une origine et une destination, fournissez votre clé ORS, puis cliquez sur *Calculer la vitesse conseillée*.")