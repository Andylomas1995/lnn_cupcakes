import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------- Paths ----------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PRICES_FILE = DATA_DIR / "prices.json"

# ---------- Base recipe (for 12 cupcakes) ----------
BASE_RECIPE = {
    "flour": {"label": "Flour", "amount": 150, "unit": "g"},
    "sugar": {"label": "Caster sugar", "amount": 150, "unit": "g"},
    "butter": {"label": "Unsalted butter", "amount": 150, "unit": "g"},
    "eggs": {"label": "Eggs", "amount": 3, "unit": "count"},
    "baking_powder": {"label": "Baking powder", "amount": 1.5, "unit": "tsp"},
    "vanilla": {"label": "Vanilla extract", "amount": 1, "unit": "tsp"},
    "milk": {"label": "Milk", "amount": 30, "unit": "g"}
}

# ---------- Helpers for prices ----------

def load_prices():
    DATA_DIR.mkdir(exist_ok=True)
    if not PRICES_FILE.exists():
        # create default file if missing
        default = {
            "flour":   {"price": 1.20, "size": 1000, "unit": "g"},
            "sugar":   {"price": 0.90, "size": 1000, "unit": "g"},
            "butter":  {"price": 2.00, "size": 250,  "unit": "g"},
            "eggs":    {"price": 2.00, "size": 12,   "unit": "count"},
            "vanilla": {"price": 3.00, "size": 50,   "unit": "ml"},
            "milk":    {"price": 1.00, "size": 1000, "unit": "ml"},
            "baking_powder": {"price": 0.80, "size": 100, "unit": "g"}
        }
        with open(PRICES_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default
    with open(PRICES_FILE) as f:
        return json.load(f)


def save_prices(prices: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(PRICES_FILE, "w") as f:
        json.dump(prices, f, indent=2)


def get_cost_for_ingredient(key, scaled_amount, prices):
    """Return cost in £ for a given ingredient amount using prices dict."""
    if key not in prices:
        return None

    info = prices[key]
    price = info.get("price")
    size = info.get("size")
    unit = info.get("unit", "g")

    if price is None or size in (None, 0):
        return None

    # eggs are by count, others by weight/volume
    if unit == "count":
        cost_per_unit = price / size
        return scaled_amount * cost_per_unit
    else:
        # assume scaled_amount is in g or ml matching size
        cost_per_unit = price / size
        return scaled_amount * cost_per_unit


# ---------- UI ----------

st.set_page_config(
    page_title="L&N CupCakes",
    page_icon="🧁",
    layout="centered"
)

st.title("🧁 L&N CupCakes")
st.caption("Batch scaler & cost calculator")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["Cupcake calculator", "Settings"])

prices = load_prices()

if page == "Cupcake calculator":
    st.subheader("Cupcake calculator")

    batch_size = st.selectbox(
        "How many cupcakes are you making?",
        options=[12, 24, 36, 48, 60],
        index=0
    )

    multiplier = batch_size / 12

    st.markdown(f"**Base recipe is for 12 cupcakes. Multiplier:** `{multiplier}x`")

    # Build scaled ingredient table
    rows = []
    total_cost = 0.0
    missing_cost = False

    for key, meta in BASE_RECIPE.items():
        label = meta["label"]
        base_amount = meta["amount"]
        unit = meta["unit"]

        scaled_amount = base_amount * multiplier

        # For tsp ingredients, we won't cost them precisely unless you want to
        if unit == "tsp":
            cost = None
        else:
            cost = get_cost_for_ingredient(key, scaled_amount, prices)

        if cost is None:
            cost_display = "—"
            missing_cost = True
        else:
            cost_display = f"£{cost:.2f}"
            total_cost += cost

        rows.append({
            "Ingredient": label,
            "Amount": f"{scaled_amount:.2f} {unit}",
            "Cost": cost_display
        })

    df = pd.DataFrame(rows)
    st.markdown("### Scaled ingredients")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total cost", f"£{total_cost:.2f}")
    with col2:
        cost_per_cupcake = total_cost / batch_size if batch_size else 0
        st.metric("Cost per cupcake", f"£{cost_per_cupcake:.2f}")

    if missing_cost:
        st.info(
            "Some ingredients are missing cost data (or use tsp). "
            "Update prices in the Settings page for full accuracy."
        )

elif page == "Settings":
    st.subheader("Settings – ingredient prices")

    st.markdown(
        "Enter the **price** you pay and the **package size** you get for each ingredient. "
        "The app will calculate cost per gram/ml/egg automatically."
    )

    updated_prices = {}

    for key, meta in BASE_RECIPE.items():
        st.markdown(f"#### {meta['label']}")
        existing = prices.get(key, {})
        default_unit = "count" if meta["unit"] == "count" else "g"

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            price = st.number_input(
                f"Price (£) for {meta['label']}",
                min_value=0.0,
                value=float(existing.get("price", 0.0)),
                step=0.10,
                key=f"{key}_price"
            )
        with col2:
            size = st.number_input(
                f"Package size ({default_unit})",
                min_value=0.0,
                value=float(existing.get("size", 0.0)),
                step=10.0 if default_unit != "count" else 1.0,
                key=f"{key}_size"
            )
        with col3:
            unit = st.selectbox(
                "Unit",
                options=["g", "ml", "count"],
                index=["g", "ml", "count"].index(existing.get("unit", default_unit)),
                key=f"{key}_unit"
            )

        updated_prices[key] = {
            "price": price,
            "size": size,
            "unit": unit
        }

        st.markdown("---")

    if st.button("💾 Save settings"):
        save_prices(updated_prices)
        st.success("Settings saved. Your calculator will now use these prices.")

