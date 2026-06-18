import streamlit as st
import numpy as np
from scipy.optimize import minimize

# App Title and Description
st.set_page_config(page_title="Brewing Water & pH Calculator", layout="centered")
st.title("🍺 FiferDave's Brewing Salts & Mash pH Calculator")
st.write("Optimize brewing salts (excluding MgCl₂) and calculate precise mash acid additions.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("🪣 Batch Settings")
volume_liters = st.sidebar.number_input("Total Water Volume (Litre)", min_value=1.0, value=20.0, step=0.5)

st.sidebar.header("💧 Base Water Profile (ppm)")
base_Ca = st.sidebar.number_input("Base Calcium (Ca)", min_value=0.0, value=10.0)
base_Mg = st.sidebar.number_input("Base Magnesium (Mg)", min_value=0.0, value=2.0)
base_Na = st.sidebar.number_input("Base Sodium (Na)", min_value=0.0, value=5.0)
base_Cl = st.sidebar.number_input("Base Chloride (Cl)", min_value=0.0, value=8.0)
base_SO4 = st.sidebar.number_input("Base Sulfate (SO4)", min_value=0.0, value=10.0)
# Alkalinity measured as Bicarbonate (HCO3) for pH modeling
base_HCO3 = st.sidebar.number_input("Base Bicarbonate (HCO3)", min_value=0.0, value=30.0, help="If report gives Total Alkalinity as CaCO3, multiply by 1.22")

# --- GRAIN BILL CONFIGURATION ---
st.sidebar.header("🌾 Grain Bill & Mash")
weight_base = st.sidebar.number_input("Base Malts (kg)", min_value=0.0, value=4.0, step=0.1, help="Pilsner, Pale, Vienna, Munich, Wheat, etc.")
weight_crystal = st.sidebar.number_input("Crystal / Caramel Malts (kg)", min_value=0.0, value=0.5, step=0.1, help="CaraPils, Crystal 40, Crystal 120, etc.")
weight_roasted = st.sidebar.number_input("Roasted Malts / Grains (kg)", min_value=0.0, value=0.2, step=0.05, help="Chocolate Malt, Roasted Barley, Black Malt")

st.sidebar.subheader("🧪 Acid Options")
acid_type = st.sidebar.selectbox("Select Mash Acid:", ["Lactic Acid Powder (100%)", "Lactic Acid Liquid (80%)", "Phosphoric Acid (10%)"])

# --- EXPANDED TARGET PROFILES DATABASE ---
st.header("🎯 Target Water Profile Selection")

style_profiles = {
    "Custom Profile (Manual Input)": {"Ca": 80.0, "Mg": 5.0, "Na": 25.0, "Cl": 90.0, "SO4": 90.0},
    "Historic: Pilsen (Soft / Pale Lager)": {"Ca": 7.0, "Mg": 2.0, "Na": 2.0, "Cl": 5.0, "SO4": 5.0},
    "Historic: Burton-on-Trent (Pale Ale / IPA)": {"Ca": 268.0, "Mg": 62.0, "Na": 30.0, "Cl": 36.0, "SO4": 820.0},
    "Historic: London (Malty Porter / Stout)": {"Ca": 52.0, "Mg": 16.0, "Na": 86.0, "Cl": 60.0, "SO4": 32.0},
    "Historic: Dublin (Dry Irish Stout)": {"Ca": 115.0, "Mg": 4.0, "Na": 12.0, "Cl": 19.0, "SO4": 55.0},
    "Historic: Munich (Märzen / Amber Lager)": {"Ca": 75.0, "Mg": 18.0, "Na": 2.0, "Cl": 30.0, "SO4": 40.0},
    "Historic: Dortmund (Export Pale Lager)": {"Ca": 250.0, "Mg": 23.0, "Na": 70.0, "Cl": 100.0, "SO4": 280.0},
    "Historic: Edinburgh (Scottish / Shilling Ales)": {"Ca": 120.0, "Mg": 25.0, "Na": 55.0, "Cl": 20.0, "SO4": 140.0},
    "Modern Style: NEIPA (Juicy / Hazy)": {"Ca": 80.0, "Mg": 5.0, "Na": 15.0, "Cl": 150.0, "SO4": 75.0},
    "Modern Style: West Coast IPA (Crisp / Bitter)": {"Ca": 100.0, "Mg": 10.0, "Na": 15.0, "Cl": 50.0, "SO4": 200.0},
    "Modern Style: Light & Hoppy (Pale Ale / Blonde)": {"Ca": 75.0, "Mg": 5.0, "Na": 10.0, "Cl": 50.0, "SO4": 150.0},
    "Modern Style: Light & Malty (Helles / Kölsch)": {"Ca": 60.0, "Mg": 5.0, "Na": 10.0, "Cl": 95.0, "SO4": 55.0},
    "Modern Style: Dark & Balanced (Brown / Stout)": {"Ca": 150.0, "Mg": 10.0, "Na": 80.0, "Cl": 150.0, "SO4": 160.0},
    "Modern Style: Belgian Ale (Saison / Dubbel)": {"Ca": 120.0, "Mg": 10.0, "Na": 20.0, "Cl": 75.0, "SO4": 75.0}
}

selected_style = st.selectbox("Choose your target baseline:", list(style_profiles.keys()))
defaults = style_profiles[selected_style]

st.write("👉 *You can manually tweak these numbers below after choosing a preset if needed:*")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: target_Ca = st.number_input("Target Ca", min_value=0.0, value=float(defaults["Ca"]))
with col2: target_Mg = st.number_input("Target Mg", min_value=0.0, value=float(defaults["Mg"]))
with col3: target_Na = st.number_input("Target Na", min_value=0.0, value=float(defaults["Na"]))
with col4: target_Cl = st.number_input("Target Cl", min_value=0.0, value=float(defaults["Cl"]))
with col5: target_SO4 = st.number_input("Target SO4", min_value=0.0, value=float(defaults["SO4"]))

# --- THE CALCULATOR LOGIC ---
base_water = {'Ca': base_Ca, 'Mg': base_Mg, 'Na': base_Na, 'Cl': base_Cl, 'SO4': base_SO4}
target_water = {'Ca': target_Ca, 'Mg': target_Mg, 'Na': target_Na, 'Cl': target_Cl, 'SO4': target_SO4}

delta_ppm = np.array([
    max(0, target_water['Ca'] - base_water['Ca']),
    max(0, target_water['Mg'] - base_water['Mg']),
    max(0, target_water['Na'] - base_water['Na']),
    max(0, target_water['Cl'] - base_water['Cl']),
    max(0, target_water['SO4'] - base_water['SO4'])
])

salt_matrix = np.array([
    [232.8,  0.0,  0.0,   0.0, 557.9],  # Gypsum
    [272.6,  0.0,  0.0, 482.2,   0.0],  # Calcium Chloride
    [  0.0, 98.6,  0.0,   0.0, 389.6],  # Epsom Salt
    [  0.0,  0.0, 273.7,  0.0,   0.0],  # Baking Soda
    [  0.0,  0.0, 393.4, 606.6,   0.0]   # Canning Salt
]).T

def objective(salts_g_per_l):
    achieved_ppm = np.dot(salt_matrix, salts_g_per_l)
    return np.sum((achieved_ppm - delta_ppm) ** 2)

result = minimize(objective, [0.1]*5, bounds=[(0, None) for _ in range(5)], method='L-BFGS-B')
total_grams = result.x * volume_liters
achieved_deltas = np.dot(salt_matrix, result.x)

# Extract salt modifications to compute final post-salt ion concentrations cleanly
final_profile = {}
profile_keys = ['Ca', 'Mg', 'Na', 'Cl', 'SO4']
for i, k in enumerate(profile_keys):
    final_profile[k] = base_water[k] + achieved_deltas[i]

# Baking soda adds bicarbonate alkalinity (1g/L adds 726 ppm HCO3)
baking_soda_g_per_l = result.x[3]
final_HCO3 = base_HCO3 + (baking_soda_g_per_l * 726.0)

# --- DISPLAY RESULTS ---
st.header("⚖️ Required Salt Additions")
salt_names = [
    "Gypsum (Calcium Sulfate)", 
    "Calcium Chloride", 
    "Epsom Salt (Magnesium Sulfate)", 
    "Baking Soda (Sodium Bicarbonate)", 
    "Canning Salt (Sodium Chloride)"
]

for name, grams in zip(salt_names, total_grams):
    if grams > 0.01:
        st.success(f"Add **{grams:.2f} grams** of {name}")
    else:
        st.info(f"0.00 grams of {name} required")

# --- MASH pH & ACID CALCULATIONS ---
st.header("🧪 Mash pH Prediction & Acid Adjustment")

total_grain_kg = weight_base + weight_crystal + weight_roasted

if total_grain_kg > 0:
    # 1. Base grain distilled water pH assumes 5.75.
    grain_ph_drop = ((weight_crystal * 0.25) + (weight_roasted * 0.55)) / total_grain_kg
    distilled_mash_ph = 5.75 - grain_ph_drop

    # 2. Account for Residual Alkalinity (RA) of adjusted water
    alkalinity_mEq = (final_HCO3 / 61.0)
    ca_mEq = (final_profile['Ca'] / 20.0)
    mg_mEq = (final_profile['Mg'] / 12.1)
    residual_alkalinity_mEq = alkalinity_mEq - (ca_mEq / 3.5) - (mg_mEq / 7.0)

    # RA shifts pH upward
    estimated_unadjusted_ph = distilled_mash_ph + (residual_alkalinity_mEq * 0.056)
    
    target_ph = 5.40
    ph_difference = estimated_unadjusted_ph - target_ph
    
    st.subheader(f"Predicted Unadjusted Mash pH: {estimated_unadjusted_ph:.2f}")

    if ph_difference > 0:
        required_mEq_total = ph_difference * 35.0 * total_grain_kg
        
        if acid_type == "Lactic Acid Powder (100%)":
            acid_needed = required_mEq_total / 11.1
            unit = "grams"
            taste_warning_limit = volume_liters * 0.27 
        elif acid_type == "Lactic Acid Liquid (80%)":
            acid_needed = required_mEq_total / 11.2
            unit = "mL"
            taste_warning_limit = volume_liters * 0.25
        else:
            acid_needed = required_mEq_total / 3.0
            unit = "mL"
            taste_warning_limit = float('inf')

        if acid_needed < 0.05:
            st.info("✨ Your mash pH is perfectly hitting the target zone. No acid additions required!")
        else:
            st.warning(f"🎯 To drop pH from {estimated_unadjusted_ph:.2f} to {target_ph:.2f}: Add **{acid_needed:.2f} {unit}** of {acid_type}")
            
            if "Lactic" in acid_type and acid_needed > taste_warning_limit:
                st.error(f"⚠️ Warning: Lactic concentration exceeds optimal flavor threshold for your volume. Consider cutting base water with RO/Distilled water to lower starting bicarbonate alkalinity.")
    else:
        st.success(f"✨ Your mash pH is predicted at {estimated_unadjusted_ph:.2f}. Dark malts have buffered your water cleanly. No acid additions required!")
else:
    st.info("ℹ️ Enter grain weights in the sidebar to calculate mash pH updates.")

# --- DISPLAY MINERAL PROFILE TABLES ---
st.header("📊 Final Water Profile Comparison")
ions = ['Calcium (Ca)', 'Magnesium (Mg)', 'Sodium (Na)', 'Chloride (Cl)', 'Sulfate (SO4)']

table_data = []
for ion, k in zip(ions, profile_keys):
    table_data.append({
        "Mineral Ion": ion,
        "Base (ppm)": f"{base_water[k]:.1f}",
        "Target (ppm)": f"{target_water[k]:.1f}",
        "Achieved (ppm)": f"{final_profile[k]:.1f}"
    })

st.table(table_data)

# Quality Checks & Feedback using pure isolated values
achieved_SO4 = final_profile['SO4']
achieved_Cl = final_profile['Cl']

if achieved_SO4 > 0:
    ratio = achieved_Cl / achieved_SO4
    st.subheader(f"Chloride to Sulfate Ratio: {ratio:.2f}")
    if ratio > 2.0: 
        st.info("🎯 Flavor Balance: Highly **Malty** profile. Perfect for accentuating roundness, sweetness, and fullness.")
    elif ratio < 0.5: 
        st.info("🎯 Flavor Balance: Highly **Bitter & Hoppy** profile. Perfect for accentuating clean crispness and intense hop bite.")
    else: 
        st.info("🎯 Flavor Balance: **Balanced** profile. Good general-purpose presentation for malt and hop expression.")
