import streamlit as st
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Scottish Brewing Water Calculator", layout="centered")
st.title("🍺 Scottish Brewing Water Calculator")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_scottish():
    df = pd.read_excel("scottish water profiles for brewing.xlsx", engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data
def load_world():
    df = pd.read_excel("worldwide water profiles.xlsx", engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    return df

scot = load_scottish()
world = load_world()

# -----------------------------
# pH GAUGE
# -----------------------------
def plot_ph_gauge(ph_value):
    fig, ax = plt.subplots(figsize=(6, 1.2))

    ax.axvspan(5.0, 5.2, color="red", alpha=0.3)
    ax.axvspan(5.2, 5.6, color="green", alpha=0.3)
    ax.axvspan(5.6, 5.8, color="orange", alpha=0.3)

    ax.axvline(ph_value, color="black", linewidth=3)

    ax.set_xlim(5.0, 5.8)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([5.0, 5.2, 5.4, 5.6, 5.8])
    ax.set_xlabel("Mash pH")

    return fig

# -----------------------------
# WATER
# -----------------------------
st.sidebar.header("🪣 Water Volumes")

mash_water = st.sidebar.number_input("Mash Water (L)", 0.0, 100.0, 15.0)
sparge_water = st.sidebar.number_input("Sparge Water (L)", 0.0, 100.0, 10.0)
total_water = mash_water + sparge_water

st.sidebar.markdown(f"**Total Water: {total_water:.1f} L**")

# -----------------------------
# BASE WATER
# -----------------------------
st.sidebar.header("💧 Base Water")

loc = st.sidebar.selectbox("Water Source Scotland - https://www.scottishwater.co.uk/your-home/your-water/water-quality/water-quality", sorted(scot["Location"].dropna()))
row = scot[scot["Location"] == loc].iloc[0]

st.sidebar.markdown("### Base Water Profile (ppm)")

base_Ca = st.sidebar.number_input("Calcium (Ca)", 0.0, 500.0, float(row["Calcium"]))
base_Mg = st.sidebar.number_input("Magnesium (Mg)", 0.0, 100.0, float(row["Magnesium"]))
base_Na = st.sidebar.number_input("Sodium (Na)", 0.0, 200.0, float(row["Sodium"]))
base_Cl = st.sidebar.number_input("Chloride (Cl)", 0.0, 500.0, float(row["Chloride"]))
base_SO4 = st.sidebar.number_input("Sulphate (SO₄)", 0.0, 500.0, float(row["Sulphate"]))
base_HCO3 = st.sidebar.number_input("Bicarbonate (HCO₃)", 0.0, 500.0, float(row["HCO3"]))

# Base water inputs above...

st.sidebar.caption(
    f"Ca:{base_Ca:.0f} Mg:{base_Mg:.0f} Na:{base_Na:.0f} "
    f"Cl:{base_Cl:.0f} SO₄:{base_SO4:.0f} HCO₃:{base_HCO3:.0f}"
)

# -----------------------------
# TARGET PROFILE
# -----------------------------
st.header("🎯 Target Profile")

profile_list = sorted(world["Location"].dropna())
profile_name = st.selectbox("Choose target profile:", profile_list)

prow = world[world["Location"] == profile_name].iloc[0]

st.markdown("### Target Water Profile (ppm)")

target_Ca = st.number_input("Calcium (Ca)", 0.0, 300.0, float(prow["Calcium"]))
target_Mg = st.number_input("Magnesium (Mg)", 0.0, 100.0, float(prow["Magnesium"]))
target_Na = st.number_input("Sodium (Na)", 0.0, 200.0, float(prow["Sodium"]))
target_Cl = st.number_input("Chloride (Cl)", 0.0, 500.0, float(prow["Chloride"]))
target_SO4 = st.number_input("Sulphate (SO₄)", 0.0, 500.0, float(prow["Sulphate"]))

# Target inputs above...

st.caption(
    f"Ca:{target_Ca:.0f} Mg:{target_Mg:.0f} Na:{target_Na:.0f} "
    f"Cl:{target_Cl:.0f} SO₄:{target_SO4:.0f}"
)

# -----------------------------
# SALTS
# -----------------------------
base = np.array([base_Ca, base_Mg, base_Na, base_Cl, base_SO4])
target = np.array([target_Ca, target_Mg, target_Na, target_Cl, target_SO4])

delta = np.maximum(target - base, 0)

matrix = np.array([
    [232.8, 0, 0, 0, 557.9],
    [272.6, 0, 0, 482.2, 0],
    [0, 98.6, 0, 0, 389.6],
    [0, 0, 273.7, 0, 0],
    [0, 0, 393.4, 606.6, 0]
]).T

def obj(x):
    return np.sum((np.dot(matrix, x) - delta) ** 2)

res = minimize(obj, [0.1]*5, bounds=[(0, None)]*5)
salts = res.x * total_water

salt_names = ["Gypsum", "Calcium Chloride", "Epsom", "Baking Soda", "Salt"]

st.header("⚖️ Salt Additions")

for name, grams in zip(salt_names, salts):
    st.write(f"{name}: {grams:.2f} g")

st.write("**Base vs Target Comparison**")

comparison = pd.DataFrame({
    "Ion": ["Ca", "Mg", "Na", "Cl", "SO₄"],
    "Base": [base_Ca, base_Mg, base_Na, base_Cl, base_SO4],
    "Target": [target_Ca, target_Mg, target_Na, target_Cl, target_SO4]
})

st.table(comparison)

# -----------------------------
# ACID SETTINGS
# -----------------------------
st.sidebar.header("🧪 Acid Settings")

acid_mode = st.sidebar.radio(
    "Apply Acid To:",
    ["Mash Only", "Sparge Only", "Mash + Sparge"]
)

acid_type = st.sidebar.selectbox(
    "Acid Type",
    [
        "Lactic Acid (liquid)",
        "Lactic Acid (powder)",
        "Phosphoric Acid",
        "Custom Acid"
    ]
)

st.sidebar.subheader("Acid Concentration")

if acid_type == "Lactic Acid (liquid)":
    acid_percent = st.sidebar.number_input("Concentration (%)", 50.0, 100.0, 80.0)

elif acid_type == "Lactic Acid (powder)":
    acid_percent = 100.0
    st.sidebar.caption("Pure lactic acid (100%)")

elif acid_type == "Phosphoric Acid":
    acid_percent = st.sidebar.number_input("Concentration (%)", 5.0, 85.0, 10.0)

else:
    acid_percent = st.sidebar.number_input("Custom Acid (%)", 1.0, 100.0, 80.0)

strength = acid_percent / 80.0

if "phosphoric" in acid_type.lower():
    strength *= 0.4

st.sidebar.caption(f"Relative strength vs 80% lactic: {strength:.2f}")

# -----------------------------
# GRAIN
# -----------------------------
st.sidebar.header("🌾 Grain Bill")

base_malt = st.sidebar.number_input(
    "Base Malt (kg)",
    min_value=0.0,
    max_value=20.0,
    value=4.0,
    step=0.05
)

crystal = st.sidebar.number_input(
    "Crystal (kg)",
    min_value=0.0,
    max_value=10.0,
    value=0.5,
    step=0.05
)

roast = st.sidebar.number_input(
    "Roasted (kg)",
    min_value=0.0,
    max_value=10.0,
    value=0.2,
    step=0.05
)


grain_total = base_malt + crystal + roast

# -----------------------------
# MASH pH
# -----------------------------
if grain_total > 0:

    grain_effect = ((crystal * 0.25) + (roast * 0.75)) / grain_total

    distilled_pH = 5.45 - grain_effect

    RA = base_HCO3 - (base_Ca / 1.4) - (base_Mg / 1.7)

    estimated_pH = distilled_pH + (RA / 100) * 0.15

    st.header("🧪 Mash pH")

    st.write(f"Estimated Mash pH: **{estimated_pH:.2f}**")

    # -----------------------------
    # pH VISUAL
    # -----------------------------
    st.markdown("### 🧪 Mash pH Visualisation")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("Before Adjustment")
        st.pyplot(plot_ph_gauge(estimated_pH))

    # -----------------------------
    # ACID
    # -----------------------------
    target_ph = st.sidebar.number_input("Target Mash pH", 5.0, 5.8, 5.4)

    delta_pH = estimated_pH - target_ph
    ml_per_l_per_0_1 = 0.1

    base_acid_ml = max(
        0,
        (delta_pH / 0.1) * ml_per_l_per_0_1 * mash_water
    )

    mash_acid_ml = base_acid_ml / strength

    alkalinity = base_HCO3 / 61
    sparge_acid_ml = (alkalinity * 0.1 * sparge_water) / strength

    if acid_mode == "Mash Only":
        sparge_acid_ml = 0
    elif acid_mode == "Sparge Only":
        mash_acid_ml = 0

    total_acid_ml = mash_acid_ml + sparge_acid_ml

    st.subheader("Acid Additions")

    if "powder" in acid_type.lower():
        grams = lambda x: x * 0.96

        if mash_acid_ml > 0:
            st.write(f"Mash: **{grams(mash_acid_ml):.2f} g**")
        if sparge_acid_ml > 0:
            st.write(f"Sparge: **{grams(sparge_acid_ml):.2f} g**")
        st.write(f"Total: **{grams(total_acid_ml):.2f} g**")

    else:
        if mash_acid_ml > 0:
            st.write(f"Mash: **{mash_acid_ml:.1f} mL**")
        if sparge_acid_ml > 0:
            st.write(f"Sparge: **{sparge_acid_ml:.1f} mL**")
        st.write(f"Total: **{total_acid_ml:.1f} mL**")

    with col2:
        st.caption("After Adjustment")
        st.pyplot(plot_ph_gauge(target_ph))

    st.success(f"Final Mash pH after adjustment: **{target_ph:.2f}**")
