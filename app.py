# Streamlit Hill of Value App (with safe plotting and type enforcement)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# --- Sidebar Inputs ---
st.title("NPVision – Hill of Value Model")

st.sidebar.header("Input Parameters")
cutoff_range = st.sidebar.slider("Cut-off Range", 0.1, 2.0, (0.2, 1.0), step=0.1)
prod_range = st.sidebar.slider("Production Range (Mtpa)", 1.0, 10.0, (2.0, 6.0), step=0.5)
metal_price_mean = st.sidebar.number_input("Metal Price Mean ($/t)", value=4000)
metal_price_std = st.sidebar.number_input("Metal Price Std Dev", value=500)
recovery_mean = st.sidebar.number_input("Recovery Mean (%)", value=85)
recovery_std = st.sidebar.number_input("Recovery Std Dev (%)", value=5)
discount_rate = st.sidebar.number_input("Discount Rate (%)", value=8.0)
opex = st.sidebar.number_input("OPEX ($/t ore)", value=40.0)

uploaded_file = st.sidebar.file_uploader("Upload Grade-Tonnage CSV", type="csv")

def grade_tonnage_curve(cutoff):
    if uploaded_file:
        user_curve = pd.read_csv(uploaded_file)
        nearest = user_curve.iloc[(user_curve['Cutoff'] - cutoff).abs().argsort()[:1]]
        return float(nearest['Tonnage']), float(nearest['Grade'])
    else:
        a = 500
        b = 0.7
        tonnage = a * (cutoff ** -b)
        grade = np.maximum(1.5 - cutoff * 0.5, 0.2)
        return tonnage, grade

def estimate_capex_schedule(total_capex, years):
    return [total_capex / 2 if t < 2 else 0 for t in range(int(np.ceil(years)))]

def estimate_capex(production):
    return 1000 + 150 * production

def calculate_npv(tonnage, grade, price, recovery, opex, production, discount_rate):
    metal_content = tonnage * grade / 100
    revenue = metal_content * recovery / 100 * price
    years = tonnage / production
    annual_cashflow = (revenue - opex * tonnage) / years
    capex = estimate_capex(production)
    capex_schedule = estimate_capex_schedule(capex, years)
    cashflows = [annual_cashflow] * int(np.ceil(years))
    npv = 0
    for t in range(int(np.ceil(years))):
        npv += (cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1))
    return npv, years, capex

cutoff_vals = np.arange(cutoff_range[0], cutoff_range[1] + 0.01, 0.1)
prod_vals = np.arange(prod_range[0], prod_range[1] + 0.01, 0.5)

scenarios = []
for cutoff in cutoff_vals:
    for prod in prod_vals:
        npvs, years_list, capex_list = [], [], []
        for _ in range(250):
            price = np.random.normal(metal_price_mean, metal_price_std)
            recovery = np.random.normal(recovery_mean, recovery_std)
            tonnage, grade = grade_tonnage_curve(cutoff)
            npv, yrs, capex_val = calculate_npv(tonnage, grade, price, recovery, opex, prod, discount_rate)
            npvs.append(npv)
            years_list.append(yrs)
            capex_list.append(capex_val)
        if npvs:
            scenarios.append({
                "Cutoff": cutoff,
                "Production": prod,
                "Avg NPV": np.mean(npvs),
                "Avg Life": np.mean(years_list),
                "CAPEX": np.mean(capex_list)
            })

if scenarios:
    df = pd.DataFrame(scenarios).dropna()

    try:
        df_clean = df.astype({
            "Cutoff": float,
            "Production": float,
            "Avg NPV": float,
            "Avg Life": float,
            "CAPEX": float
        })
        df_clean = df_clean[(df_clean["Avg NPV"] > 0) & (df_clean["CAPEX"] > 0) & (df_clean["Avg Life"] > 0)]

        st.subheader("Scenario Results")
        st.dataframe(df_clean.style.format("{:.2f}"))

        st.subheader("Visualizations")
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.scatter(
                df_clean, x="Production", y="CAPEX", color="Cutoff", size="Avg NPV",
                labels={"CAPEX": "CAPEX ($M)", "Production": "Production (Mtpa)"})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.scatter(
                df_clean, x="Cutoff", y="Avg Life", color="Production", size="Avg NPV",
                labels={"Avg Life": "Mine Life (Years)"})
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Hill of Value – 3D NPV Surface")
        try:
            z_data = df_clean.pivot_table(index='Cutoff', columns='Production', values='Avg NPV').values
            fig3 = go.Figure(data=[
                go.Surface(
                    z=z_data,
                    x=prod_vals,
                    y=cutoff_vals,
                    colorscale='Viridis',
                    hovertemplate="<b>Cutoff</b>: %{y}<br><b>Production</b>: %{x}<br><b>NPV</b>: %{z:.2f}M",
                    showscale=True
                )
            ])
            fig3.update_layout(
                scene=dict(
                    xaxis_title='Production (Mtpa)',
                    yaxis_title='Cut-off Grade (%)',
                    zaxis_title='Avg NPV ($M)'
                ),
                margin=dict(l=20, r=20, t=30, b=20),
                height=800
            )
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.warning(f"3D plot error: {e}")

        st.download_button("Download Results CSV", df_clean.to_csv(index=False), file_name="hill_of_value_results.csv")

    except Exception as err:
        st.error(f"❌ Error while cleaning or plotting data: {err}")
else:
    st.warning("No valid scenarios generated. Please adjust input parameters.")
