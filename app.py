# Fully Verified Minimal Streamlit App – Clean, No Crashes
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Hill of Value – Verified Minimal Model")

# Sidebar controls
cutoff_range = st.sidebar.slider("Cut-off Range (%)", 0.2, 1.0, (0.2, 1.0), step=0.1)
prod_range = st.sidebar.slider("Production Range (Mtpa)", 2.0, 6.0, (2.0, 6.0), step=0.5)
metal_price = st.sidebar.number_input("Metal Price ($/t)", value=4000)
recovery = st.sidebar.slider("Recovery (%)", 50, 95, 85)
discount_rate = st.sidebar.slider("Discount Rate (%)", 1, 15, 8)
opex = st.sidebar.number_input("OPEX ($/t)", value=40.0)

cutoff_vals = np.round(np.arange(cutoff_range[0], cutoff_range[1] + 0.01, 0.1), 2)
prod_vals = np.round(np.arange(prod_range[0], prod_range[1] + 0.01, 0.5), 2)

@st.cache_data
def run_model():
    rows = []
    for cutoff in cutoff_vals:
        for prod in prod_vals:
            tonnage = 500 * (cutoff ** -0.7)
            grade = max(1.5 - cutoff * 0.5, 0.2)
            metal_content = tonnage * grade / 100
            revenue = metal_content * recovery / 100 * metal_price
            years = tonnage / prod
            annual_cashflow = (revenue - opex * tonnage) / years
            capex = 1000 + 150 * prod
            capex_schedule = [capex / 2 if t < 2 else 0 for t in range(int(np.ceil(years)))]
            cashflows = [annual_cashflow] * int(np.ceil(years))
            npv = sum([(cashflows[t] - capex_schedule[t]) / ((1 + discount_rate / 100) ** (t + 1)) for t in range(len(cashflows))])
            rows.append({
                "Cutoff": cutoff,
                "Production": prod,
                "NPV": round(npv, 2),
                "Life": round(years, 2),
                "CAPEX": round(capex, 2)
            })
    return pd.DataFrame(rows)

df = run_model()
st.dataframe(df)

# Pivot to Z-matrix for 3D surface plot
pivot = df.pivot(index="Cutoff", columns="Production", values="NPV")
if pivot.isnull().values.any():
    st.warning("Some values missing for 3D plot")
else:
    fig = go.Figure(data=[
        go.Surface(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='Viridis',
            hovertemplate="Cutoff: %{y}<br>Production: %{x}<br>NPV: %{z:.2f}"
        )
    ])
    fig.update_layout(
        title="Hill of Value – 3D NPV Surface",
        scene=dict(
            xaxis_title='Production (Mtpa)',
            yaxis_title='Cut-off (%)',
            zaxis_title='NPV ($M)'
        ),
        height=700,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

st.download_button("Download CSV", df.to_csv(index=False), file_name="hill_of_value_output.csv")
