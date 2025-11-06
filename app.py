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
import os

# ------------------------------
# App Config
# ------------------------------
st.set_page_config(page_title="EV Eco-Speed Advisory App", layout="wide", page_icon="🚗")

# Clé ORS par défaut (peut être surchargée par st.secrets ou l'environnement)
DEFAULT_ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjA5MDkyNTdkYTlmNzQ5NmNhNjMxNzVjZGM1NTE0ZWYzIiwiaCI6Im11cm11cjY0In0="

def get_ors_key() -> str:
    """Récupère la clé ORS depuis secrets/env sans planter si secrets.toml est absent."""
    # 1) Essayer st.secrets sans faire planter si le fichier n'existe pas
    try:
        if hasattr(st, "secrets") and "OPENROUTESERVICE_API_KEY" in st.secrets:  # type: ignore[attr-defined]
            return str(st.secrets["OPENROUTESERVICE_API_KEY"])  # type: ignore[index]
    except Exception:
        pass
    # 2) Variable d'environnement
    env_val = os.environ.get("OPENROUTESERVICE_API_KEY")
    if env_val:
        return env_val
    # 3) Valeur par défaut
    return DEFAULT_ORS_API_KEY

try:
    plt.style.use('seaborn-v0_8-whitegrid')
except Exception:
    pass

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

# Custom logo and header
st.markdown("""
<div class="logo-container">
    <span class="logo-emoji">🚗🔋⚡</span>
    <h1 style="margin: 0; color: #2c3e50;">EV Eco-Speed Optimizer</h1>
    <p style="margin-top: 0.5rem; color: #7f8c8d; font-size: 1.1rem;">
        Plan trips intelligently by optimizing your energy consumption
    </p>
</div>
""", unsafe_allow_html=True)

# Add information about new features
with st.expander("ℹ️ What's new and features", expanded=False):
    st.markdown("""
        **✨ Recent improvements:**
        - 👥 Consideration of the **number of passengers and their weight**
        - 🌡️ **HVAC settings** for more accurate calculations
        - 🔋 **Charging planning**: battery percentage at departure and arrival
        - 📊 **Improved charts** with optimized data visualization
        - 🚦 **New: Speed limits by segment**: automatic consideration of limits by road type (motorway 130 km/h, primary 90 km/h, city 50 km/h, etc.)
        - 🛣️ **Improved intersection detection**: precise identification of intersections, roundabouts and slow-down points
        
        This tool helps you:
        - Maximize your EV driving range
        - Reduce your energy costs
        - Plan your charging stops
        - Get more realistic consumption estimates with speeds adapted to real limits
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
    # Sidebar logo
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🚗⚡</div>
        <div style="font-weight: 600; color: #667eea; font-size: 1.1rem;">EV Optimizer</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.header("⚙️ Settings")
    
    # Quick help
    with st.expander("💡 Tip", expanded=False):
        st.markdown("""
        **Factors that affect your consumption:**
        - 🧍 **Weight**: More passengers = higher consumption
        - 🌡️ **HVAC**: Can increase consumption by 10–30%
        - 🏔️ **Topography**: Uphill segments significantly increase consumption
        - 🏎️ **Speed**: Consumption rises exponentially with speed
        - 🌡️ **Temperature**: Extreme cold/heat reduces battery efficiency
        """)
    
    # ORS API Key info (utilisée automatiquement)
    ors_key = get_ors_key()
    st.caption("Using configured OpenRouteService API key")
    st.markdown("---")
    
    # Vehicle profile
    st.subheader("🚗 Vehicle profile")
    vehicle_profile = st.selectbox("Model", list(VEHICLE_PROFILES.keys()))
    
    if vehicle_profile != "Personnalisé":
        profile = VEHICLE_PROFILES[vehicle_profile]
        st.info(f"Profile {vehicle_profile} loaded")
        st.caption(f"Battery: {profile['battery_kwh']} kWh | Aux: {profile['aux_power_kw']} kW")

    st.markdown("---")
    st.subheader("Vehicle parameters")
    
    # Utiliser les valeurs du profil ou permettre la personnalisation
    if vehicle_profile != "Personnalisé":
        profile = VEHICLE_PROFILES[vehicle_profile]
        mass_kg = st.number_input("Mass (kg)", 1000, 3500, profile["mass_kg"], 50, disabled=True)
        cda = st.number_input("Frontal area × Cd (CdA in m²)", 0.3, 1.2, profile["cda"], 0.01, disabled=True)
        crr = st.number_input("Rolling resistance (Crr)", 0.005, 0.02, profile["crr"], 0.001, format="%.3f", disabled=True)
        eta_drive = st.slider("Drivetrain efficiency (η)", 0.70, 0.98, profile["eta_drive"], 0.01, disabled=True)
        regen_eff = st.slider("Regeneration efficiency (%)", 0, 90, int(profile["regen_eff"]*100), 5, disabled=True) / 100.0
        aux_power_kw = st.number_input("Auxiliary power (kW)", 0.0, 5.0, profile["aux_power_kw"], 0.1, disabled=True)
        battery_kwh = st.number_input("Battery capacity (kWh)", 20, 150, profile["battery_kwh"], 5, disabled=True)
    else:
        mass_kg = st.number_input("Mass (kg)", 1000, 3500, 1900, 50)
        cda = st.number_input("Frontal area × Cd (CdA in m²)", 0.3, 1.2, 0.62, 0.01)
        crr = st.number_input("Rolling resistance (Crr)", 0.005, 0.02, 0.010, 0.001, format="%.3f")
        eta_drive = st.slider("Drivetrain efficiency (η)", 0.70, 0.98, 0.90, 0.01)
        regen_eff = st.slider("Regeneration efficiency (%)", 0, 90, 60, 5) / 100.0
        aux_power_kw = st.number_input("Auxiliary power (kW)", 0.0, 5.0, 2.0, 0.1)
        battery_kwh = st.number_input("Battery capacity (kWh)", 20, 150, 60, 5)

    st.markdown("---")
    st.subheader("🌡️ Environment (simplified)")
    headwind_ms = st.number_input("Headwind (+) / Tailwind (-) (m/s)", -20.0, 20.0, 0.0, 0.5)
    ambient_temp_c = st.number_input("Ambient temperature (°C)", -30.0, 50.0, 20.0, 1.0)
    is_raining = st.checkbox("Rain (higher rolling resistance)", value=False)

    st.markdown("---")
    st.subheader("Candidate speeds (km/h)")
    default_speeds = list(range(50, 131, 5))
    speeds_str = st.text_input("Comma-separated list", ", ".join(map(str, default_speeds)))
    try:
        candidate_speeds = sorted({int(s.strip()) for s in speeds_str.split(",") if s.strip()})
    except Exception:
        candidate_speeds = default_speeds
    user_speed_limit = st.number_input("Max speed on route (km/h)", 50, 130, 110, 10, help="To stay realistic if the API does not return a limit.")
    st.markdown("---")
    st.subheader("Constraints / Objective")
    max_time_penalty_pct = st.slider("Max time increase vs fastest speed (%)", 0, 50, 15, 1)
    minimize_target = st.selectbox("Objective", ["Minimize energy under time constraint", "Weighted score (E + λ·T)"])
    lam = st.slider("λ (time weight) [for weighted score]", 0.0, 10.0, 2.0, 0.5)
    
    st.markdown("---")
    st.subheader("👥 Load and passengers")
    num_passengers = st.number_input("Number of passengers", 0, 7, 1, 1, help="Driver included")
    avg_weight_kg = st.number_input("Average weight per person (kg)", 40, 120, 75, 5)
    total_passenger_weight = num_passengers * avg_weight_kg
    
    st.markdown("---")
    st.subheader("🌡️ Driving conditions")
    use_climate = st.checkbox("Use HVAC", value=False)
    if use_climate:
        climate_intensity = st.slider("HVAC intensity (%)", 0, 100, 50, 10)
    else:
        climate_intensity = 0
    
    st.markdown("---")
    st.subheader("🔋 Battery state")
    battery_start_pct = st.slider("Battery at departure (%)", 20, 100, 100, 5)
    battery_end_pct = st.slider("Target battery on arrival (%)", 5, 90, 20, 5)
    
    st.markdown("---")
    st.subheader("Advanced options")
    use_elevation = st.checkbox("Use elevation data", value=True, help="Disable if you encounter API errors")
    use_segmented_speeds = st.checkbox("Speed limits by segment", value=True, help="Takes into account limits by road type (motorway, city, etc.)")
    if use_segmented_speeds:
        min_speed_delta = st.number_input("Minimum speed delta (km/h)", 0, 50, 20, 5, help="Minimum speed = limit - delta (e.g., motorway 130 with delta 20 → min 110 km/h)")
    else:
        min_speed_delta = 0
    use_detailed_route = st.checkbox("Detailed route", value=True, help="Disable for short trips")
    debug_mode = st.checkbox("Debug mode", value=False, help="Display intermediate information")

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

def seg_energy_and_time(distance_m, slope, speed_kmh, mass_kg, cda, crr, rho_air, eta_drive, regen_eff, aux_power_kw=0, headwind_ms=0.0, temp_c=20.0, rain=False, **kwargs):
    """
    distance_m : segment length in meters
    slope      : dh/dx (rise over run). Positive uphill.
    speed_kmh  : vehicle speed (km/h), assumed constant over the segment
    headwind_ms: positive = headwind, negative = tailwind
    rain       : increases rolling resistance
    returns    : (energy_Wh, time_hours)
    """
    if distance_m <= 0 or speed_kmh <= 0:
        return 0.0, 0.0

    slope = max(-0.5, min(0.5, slope))

    v = max(speed_kmh, 1e-3) * (1000/3600)  # vehicle ground speed (m/s)
    v_air = max(v - headwind_ms, 0.0)        # relative air speed (m/s)

    # Aerodynamic drag power (with wind)
    F_aero = 0.5 * rho_air * cda * v_air * v_air

    # Rolling resistance (rain increases Crr slightly)
    crr_eff = crr * (1.15 if rain else 1.0)
    F_roll = crr_eff * mass_kg * g * math.cos(math.atan(slope))

    F_grade = mass_kg * g * math.sin(math.atan(slope))

    P_wheels = (F_aero + F_roll + F_grade) * v  # power at wheels depends on ground speed

    if P_wheels >= 0:
        P_elec = P_wheels / max(eta_drive, 1e-6)
    else:
        P_elec = P_wheels * regen_eff

    # Temperature-driven HVAC adjustment (simple): add 0–1.5 kW if |temp-20| up to 20°C
    temp_penalty_kw = min(abs(temp_c - 20.0) / 20.0, 1.0) * 1.5
    P_aux = (aux_power_kw + temp_penalty_kw) * 1000

    P_total = P_elec + P_aux
    t = distance_m / max(v, 1e-6)
    E_Wh = P_total * (t / 3600.0)
    return E_Wh, t / 3600.0


def route_energy_time_detailed(coords, elevations, speed_kmh, env, **veh):
    """Return total metrics and a per-segment dataframe.
    env: dict with headwind_ms, temp_c, rain
    """
    records = []
    total_E = total_T = total_D = 0.0
    is_speed_list = isinstance(speed_kmh, list)
    if is_speed_list and len(speed_kmh) != len(coords) - 1:
        speed_kmh = speed_kmh[0] if speed_kmh else 50
        is_speed_list = False

    for i in range(1, len(coords)):
        if len(coords[i-1]) < 2 or len(coords[i]) < 2:
            continue
        lon1, lat1 = coords[i-1][0], coords[i-1][1]
        lon2, lat2 = coords[i][0], coords[i][1]
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = R * c
        if d < 1e-2:
            continue
        h1 = elevations[i-1]
        h2 = elevations[i]
        slope = (h2 - h1) / max(d, 1e-6)
        seg_speed = speed_kmh[i-1] if is_speed_list else speed_kmh
        E_Wh, T_h = seg_energy_and_time(d, slope, seg_speed, headwind_ms=env.get("headwind_ms",0.0), temp_c=env.get("temp_c",20.0), rain=env.get("rain",False), **veh)
        total_E += E_Wh
        total_T += T_h
        total_D += d
        records.append(dict(index=i-1, distance_m=d, slope=slope, speed_kmh=seg_speed, energy_Wh=E_Wh, time_s=T_h*3600.0, elev1=h1, elev2=h2, lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2))
    df = pd.DataFrame(records)
    return (total_E, total_T, total_D/1000.0), df

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
# Predefined typical routes
# ------------------------------
TYPICAL_ROUTES = {
    "Paris → Lyon": ("Paris, France", "Lyon, France"),
    "Paris → Marseille": ("Paris, France", "Marseille, France"),
    "Paris → Toulouse": ("Paris, France", "Toulouse, France"),
    "Paris → Nantes": ("Paris, France", "Nantes, France"),
    "Lyon → Marseille": ("Lyon, France", "Marseille, France"),
    "Custom": ("", "")
}

# ------------------------------
# Main UI
# ------------------------------
st.markdown("### 1) Enter your trip")

# Route selection
route_choice = st.selectbox("Choose a typical route", list(TYPICAL_ROUTES.keys()))

if route_choice != "Custom":
    orig_text, dest_text = TYPICAL_ROUTES[route_choice]
    st.info(f"Selected route: {route_choice}")
else:
    orig_text = ""
    dest_text = ""

col1, col2 = st.columns(2)
with col1:
    orig_text = st.text_input("Origin (address or city)", orig_text)
with col2:
    dest_text = st.text_input("Destination (address or city)", dest_text)

run_btn = st.button("Compute advised speed")

if run_btn:
    # ORS API Key via helper sûr
    ors_key = get_ors_key()
    if not ors_key or not is_valid_ors_key(ors_key):
        st.error("Invalid OpenRouteService API key. Paste your ORS key (not an error message).")
        st.stop()

    with st.spinner("Geocoding addresses..."):
        start = ors_geocode(orig_text, ors_key)
        end = ors_geocode(dest_text, ors_key)
        if not start or not end:
            st.error("Geocoding failed. Try more precise addresses.")
            st.stop()

    with st.spinner("Computing route..."):
        try:
            coords, length_m, duration_s = ors_route(start, end, ors_key)
            if not coords or len(coords) < 2:
                st.error("No route found.")
                st.stop()
        except Exception as e:
            st.error(f"Error while computing route: {e}")
            st.stop()

    with st.spinner("Fetching elevation profile..."):
        if not use_elevation:
            st.info("Elevation disabled - Using constant altitude")
            elevations = [0.0 for _ in coords]
        else:
            try:
                # Pour les petits trajets, essayer une approche simplifiée
                if len(coords) <= 2:
                    st.info("Short trip - Using constant elevation for simplicity")
                    elevations = [0.0 for _ in coords]
                else:
                    elevations = ors_elevation_along(coords, ors_key)
                    # Validation que les élévations ont la même longueur que les coordonnées
                    if len(elevations) != len(coords):
                        st.warning(f"Elevation length ({len(elevations)}) differs from coordinates ({len(coords)}). Using constant elevation.")
                        elevations = [0.0 for _ in coords]
            except Exception as e:
                st.warning(f"Elevation unavailable ({e}). Assuming constant altitude.")
                elevations = [0.0 for _ in coords]

    if debug_mode:
        st.caption("[DEBUG] Lengths after elevation")
        st.json({"n_coords": len(coords), "n_elev": len(elevations)})
        try:
            if elevations:
                import numpy as np
                arr = np.array(elevations, dtype=float)
                st.caption("[DEBUG] Elevation stats")
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
        st.error("Invalid route: fewer than 2 points")
        st.stop()
    
    # Si on n'a que 2 points (départ/arrivée), créer un itinéraire simplifié
    if len(coords) == 2:
        st.warning("⚠️ Simplified route: only 2 points (start/end)")
        st.info("Calculations will be based on a straight line. For better accuracy, try closer cities.")
        
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
        st.error("Inconsistent data: elevation and coordinate counts differ")
        st.stop()

    st.success("Route and elevations retrieved ✅")

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
    with st.spinner("Analyzing intersections and speed limits..."):
        steps, detailed_segments = ors_route_steps(start, end, ors_key)
        intersection_data = detect_intersections_improved(steps, detailed_segments, coords)
        slowdown_count = len(intersection_data["intersections"]) + len(intersection_data["slowdown_points"])
    if debug_mode:
        st.caption("[DEBUG] Raw recap after route retrieval")
        st.json({
            "n_coords": len(coords),
            "length_m": length_m,
            "duration_s": duration_s,
        })

    # Pas de segmentation avancée ni carte dans la version d'origine

    # (debug segments supprimé)

    # Environment pack for calculations
    env = dict(headwind_ms=headwind_ms, temp_c=ambient_temp_c, rain=is_raining)

    # Build vehicle parameters dict with validation
    try:
        climate_power_adjustment = (climate_intensity / 100.0) * 3.0 if use_climate else 0.0
        adjusted_aux_power = float(aux_power_kw) + climate_power_adjustment
        total_mass_kg = float(mass_kg) + float(total_passenger_weight)
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
        if veh['mass_kg'] <= 0 or veh['eta_drive'] <= 0 or veh['eta_drive'] > 1:
            st.error("Invalid vehicle parameters")
            st.stop()
    except (ValueError, TypeError) as e:
        st.error(f"Error in vehicle parameters: {e}")
        st.stop()

    # Limit candidate speeds by user setting
    candidates = [v for v in candidate_speeds if v <= user_speed_limit]
    if not candidates:
        candidates = [user_speed_limit]

    # Evaluate with progress bar (with segmented speeds)
    results = []
    fastest_t = None

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, v in enumerate(candidates):
        status_text.text(f"Computing for {v} km/h (with per-segment limits)...")
        progress_bar.progress((i + 1) / len(candidates))

        try:
            if use_segmented_speeds and steps and detailed_segments:
                segmented_speeds = create_segmented_speeds(coords, steps, detailed_segments, v, user_speed_limit, min_speed_delta)
                if intersection_data["slowdown_points"]:
                    for slowdown in intersection_data["slowdown_points"]:
                        step_idx = slowdown.get("step_index", 0)
                        if steps and len(steps) > 0:
                            coord_ratio = step_idx / max(len(steps), 1)
                            coord_idx = min(int(coord_ratio * (len(coords) - 1)), len(segmented_speeds) - 1)
                            if 0 <= coord_idx < len(segmented_speeds):
                                segmented_speeds[coord_idx] = max(segmented_speeds[coord_idx] * 0.7, 30)
                (E_Wh, T_h, D_km), _ = route_energy_time_detailed(coords, elevations, segmented_speeds, env, **veh)
                avg_speed = sum(segmented_speeds) / len(segmented_speeds) if segmented_speeds else v
            else:
                (E_Wh, T_h, D_km), _ = route_energy_time_detailed(coords, elevations, v, env, **veh)
                avg_speed = v

            results.append(dict(speed=v, energy_Wh=E_Wh, time_h=T_h, dist_km=D_km, avg_speed=avg_speed))
            if fastest_t is None or T_h < fastest_t:
                fastest_t = T_h
        except Exception as e:
            st.warning(f"Error for {v} km/h: {e}")
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
        feasible = results[:]  # fallback if no reference time

    if not feasible:
        st.error("No valid result found")
        st.stop()
    
    if minimize_target == "Minimize energy under time constraint":
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
    st.markdown("### 2) Results")
    
    # Calcul du nombre de recharges nécessaires
    energy_needed_kwh = best['energy_Wh'] / 1000
    charge_info = calculate_charging_stops(battery_kwh, energy_needed_kwh, battery_start_pct, battery_end_pct)
    
    # Energy cost
    energy_cost_per_kwh = st.sidebar.number_input("Electricity cost (€/kWh)", 0.10, 0.50, 0.20, 0.01)
    energy_cost = energy_needed_kwh * energy_cost_per_kwh
    
    # Battery at departure and calculated for arrival
    battery_start_kwh = battery_kwh * (battery_start_pct / 100.0)
    battery_after_trip = battery_start_kwh - energy_needed_kwh
    battery_end_pct_calc = (battery_after_trip / battery_kwh) * 100
    
    # Show a summary of trip parameters
    with st.expander("📋 Trip parameter summary", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 Passengers", f"{num_passengers}", help=f"Total weight: {total_passenger_weight} kg")
        col2.metric("🌡️ HVAC", "✅ Yes" if use_climate else "❌ No", help=f"Intensity: {climate_intensity}%" if use_climate else "")
        col3.metric("🔋 Battery (start)", f"{battery_start_pct}%", help=f"{battery_start_kwh:.1f} kWh")
        col4.metric("🎯 Battery target", f"{battery_kwh * (battery_end_pct/100):.1f} kWh")
    
    # Show battery information
    st.info(f"📊 **Battery analysis**: Start {battery_start_pct}% ({battery_start_kwh:.1f} kWh) | After trip: {battery_end_pct_calc:.1f}% ({battery_after_trip:.1f} kWh)")
    
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Advised speed", f"{best['speed']} km/h")
    colB.metric("Estimated energy", f"{energy_needed_kwh:.2f} kWh")
    colC.metric("Travel time", f"{best['time_h']*60:.1f} min")
    colD.metric("Distance", f"{best['dist_km']:.1f} km")

    # Relief and intersections block
    colR1, colR2, colR3 = st.columns(3)
    colR1.metric("Elevation gain", f"{total_up_m:.0f} m")
    colR2.metric("Elevation loss", f"{total_down_m:.0f} m")
    colR3.metric("Max slope (abs)", f"{max_abs_slope_pct:.1f} %")

    st.caption("Detected intersections/slowdowns (improved analysis)")
    col_int1, col_int2 = st.columns(2)
    col_int1.metric("Intersections", len(intersection_data["intersections"]))
    col_int2.metric("Slowdown points", len(intersection_data["slowdown_points"]))
    
    if use_segmented_speeds:
        st.success("✅ **Per-segment speed limits enabled**: Calculations consider limits by road type (motorway 130 km/h, city 50 km/h, etc.)")
        if 'avg_speed' in best:
            st.info(f"ℹ️ Actual average speed on the route: {best['avg_speed']:.1f} km/h (base advised speed: {best['speed']} km/h)")
    
    # New metrics with charging
    colE, colF, colG, colH = st.columns(4)
    colE.metric("Energy cost", f"{energy_cost:.2f} €")
    colF.metric("🔌 Required charges", f"{charge_info['num_stops']}", help="Number of charges to plan")
    colG.metric("Battery after trip", f"{battery_end_pct_calc:.1f}%")
    colH.metric("Consumption", f"{energy_needed_kwh/best['dist_km']:.2f} kWh/km")
    
    # Charging result display
    if charge_info['num_stops'] == 0:
        st.success(f"✅ **No charging needed!** You have enough battery for this trip.")
    elif charge_info['num_stops'] > 0 and charge_info['num_stops'] < 10:
        st.warning(f"🔋 **{charge_info['num_stops']} charge(s) recommended** for this trip.")
    else:
        st.error(f"⚠️ **Challenging trip**: Consumption is very high ({charge_info['num_stops']} estimated charges).")
    
    # Alerts for edge cases
    if battery_end_pct_calc < 20:
        st.error("⚠️ Very low battery on arrival! Consider charging before departure.")
    elif battery_end_pct_calc < 50:
        st.warning("🔋 Moderate battery level on arrival. Monitor your consumption.")
    
    if energy_needed_kwh > veh['battery_kwh']:
        st.error("❌ Consumption exceeds battery capacity! Trip is not feasible.")
    elif energy_needed_kwh > veh['battery_kwh'] * 0.8:
        st.warning("⚠️ High consumption. Trip is possible but risky.")

    # Savings vs fastest
    dE_Wh = best["energy_Wh"] - fastest["energy_Wh"]
    dT_min = (best["time_h"] - fastest["time_h"]) * 60
    st.markdown("#### Impact vs fastest driving (among your candidate speeds)")
    c1, c2 = st.columns(2)
    c1.metric("Energy saved", f"{-dE_Wh/1000:.2f} kWh" if dE_Wh<0 else f"+{dE_Wh/1000:.2f} kWh")
    c2.metric("Time added", f"{dT_min:.1f} min")

    # ------------------------------
    # Table results
    # ------------------------------
    st.markdown("#### Comparison of candidate speeds")
    import pandas as pd
    df = pd.DataFrame([
        dict(
            Speed_kmh=r["speed"],
            Energy_kWh=r["energy_Wh"]/1000.0,
            Time_min=r["time_h"]*60.0
        ) for r in results
    ]).sort_values("Speed_kmh")
    st.dataframe(df, use_container_width=True)

    # ------------------------------
    # Plot Energy vs Speed (improved)
    # ------------------------------
    col_graph1, col_graph2 = st.columns(2)

    # Feasible mask under time constraint
    max_time_h = fastest_t * (1 + max_time_penalty_pct/100.0) if fastest_t is not None else None
    feasible_speeds = set(r["speed"] for r in results if max_time_h is None or r["time_h"] <= max_time_h)

    with col_graph1:
        fig_energy, ax = plt.subplots(figsize=(8.5, 5.2))
        x = df["Speed_kmh"].values
        yE = df["Energy_kWh"].values
        colors = ["#2ecc71" if int(s) in feasible_speeds else "#3498db" for s in x]
        ax.plot(x, yE, color="#95a5a6", linewidth=1.0, linestyle="--", alpha=0.6)
        ax.scatter(x, yE, s=100, c=colors, alpha=0.85, edgecolors='black', linewidth=0.8)
        # Annotate best
        ax.scatter(best["speed"], best["energy_Wh"]/1000, s=220, c="#e74c3c", marker='*', edgecolors='black', linewidth=0.8, zorder=5)
        ax.annotate(
            f"Best: {best['speed']} km/h\n{best['energy_Wh']/1000:.2f} kWh",
            xy=(best["speed"], best["energy_Wh"]/1000), xycoords='data',
            xytext=(15, 10), textcoords='offset points',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#e74c3c", lw=1),
            arrowprops=dict(arrowstyle="->", color="#e74c3c")
        )
        ax.set_xlabel("Speed (km/h)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Energy (kWh)", fontsize=12, fontweight='bold')
        ax.set_title("⚡ Energy vs Speed (green = feasible under time constraint)", fontsize=13, pad=12)
        ax.grid(True, alpha=0.25, linestyle=':')
        plt.tight_layout()
        st.pyplot(fig_energy)

    with col_graph2:
        fig_time, ax = plt.subplots(figsize=(8.5, 5.2))
        yT = df["Time_min"].values
        ax.plot(x, yT, color="#95a5a6", linewidth=1.0, linestyle="--", alpha=0.6)
        ax.scatter(x, yT, s=100, c=["#2ecc71" if int(s) in feasible_speeds else "#e67e22" for s in x], alpha=0.85, edgecolors='black', linewidth=0.8)
        ax.scatter(best["speed"], best["time_h"]*60, s=220, c="#e74c3c", marker='*', edgecolors='black', linewidth=0.8, zorder=5)
        ax.annotate(
            f"Best: {best['speed']} km/h\n{best['time_h']*60:.1f} min",
            xy=(best["speed"], best["time_h"]*60), xycoords='data',
            xytext=(15, -25), textcoords='offset points',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#e74c3c", lw=1),
            arrowprops=dict(arrowstyle="->", color="#e74c3c")
        )
        if max_time_h is not None:
            ax.axhline(max_time_h*60.0, color="#2ecc71", linestyle=":", linewidth=1.2, alpha=0.8, label="Max allowed time")
            ax.legend(loc="best", fontsize=10)
        ax.set_xlabel("Speed (km/h)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Time (minutes)", fontsize=12, fontweight='bold')
        ax.set_title("⏱️ Time vs Speed (green = feasible)", fontsize=13, pad=12)
        ax.grid(True, alpha=0.25, linestyle=':')
        plt.tight_layout()
        st.pyplot(fig_time)

    st.info("Tip: Adjust 'Max speed' and the 'Max time increase' in the sidebar to see the effect on the recommendation.")

    # Detailed dataframe for chosen strategy (for export and map)
    if use_segmented_speeds and steps and detailed_segments:
        segmented_speeds_best = create_segmented_speeds(coords, steps, detailed_segments, best['speed'], user_speed_limit, min_speed_delta)
        (E_best, T_best, D_best), df_segments = route_energy_time_detailed(coords, elevations, segmented_speeds_best, env, **veh)
    else:
        (E_best, T_best, D_best), df_segments = route_energy_time_detailed(coords, elevations, best['speed'], env, **veh)

    # ------------------------------
    # Download per-segment CSV
    # ------------------------------
    st.markdown("#### Per-segment analytics")
    st.dataframe(df_segments.head(20), use_container_width=True)
    csv_bytes = df_segments.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download per-segment CSV", data=csv_bytes, file_name="segments.csv", mime="text/csv")

    # ------------------------------
    # Optional interactive map (Folium)
    # ------------------------------
    show_map = st.checkbox("Show interactive map (per-segment colors)", value=False)
    if show_map:
        try:
            import folium
            from streamlit_folium import st_folium
            # Center map
            mid = len(coords)//2
            center = [coords[mid][1], coords[mid][0]] if coords else [48.8566, 2.3522]
            m = folium.Map(location=center, zoom_start=6)
            # Color function by speed
            def speed_color(v):
                if v >= 110:
                    return '#2ecc71'
                if v >= 80:
                    return '#3498db'
                return '#e67e22'
            # Draw segments
            for idx, row in df_segments.iterrows():
                v = row['speed_kmh']
                color = speed_color(v)
                folium.PolyLine([(row['lat1'], row['lon1']), (row['lat2'], row['lon2'])], color=color, weight=4, opacity=0.8).add_to(m)
            st_folium(m, width=900, height=500)
        except Exception as e:
            st.warning(f"Map unavailable: {e}")

else:
    st.info("Enter an origin and a destination, provide your ORS key, then click *Compute advised speed*.")