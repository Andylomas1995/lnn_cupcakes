import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------- Paths ----------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PRICES_FILE = DATA_DIR / "prices.json"
BUTTERCREAM_MISC_FILE = DATA_DIR / "buttercream_misc.json"
MISC_FILE = DATA_DIR / "misc.json"

# ---------- Base recipes (for 12 cupcakes) ----------

CUPCAKE_RECIPE = {
    "flour": {"label": "Flour", "amount": 225, "unit": "g"},
    "sugar": {"label": "Caster sugar", "amount": 225, "unit": "g"},
    "butter": {"label": "Unsalted butter", "amount": 225, "unit": "g"},
    "eggs": {"label": "Eggs", "amount": 4, "unit": "count"},
    "vanilla": {"label": "Vanilla extract", "amount": 1, "unit": "tsp"}
}

BUTTERCREAM_RECIPE = {
    "butter": {"label": "Unsalted butter", "amount": 226, "unit": "g"},
    "icing_sugar": {"label": "Icing sugar", "amount": 360, "unit": "g"},
    "vanilla": {"label": "Vanilla extract", "amount": 1, "unit": "tbsp"},
    "milk": {"label": "Whole milk", "amount": 2, "unit": "tbsp"}
}

# ---------- Helpers: file IO ----------

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def load_json(path: Path, default):
    ensure_data_dir()
    if not path.exists():
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
        return default

def save_json(path: Path, data):
    ensure_data_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
# ---------- Loaders ----------

def load_prices():
    default = {
        "cupcake": {
            "flour":   {"price": 1.20, "size": 1000, "unit": "g"},
            "sugar":   {"price": 0.90, "size": 1000, "unit": "g"},
            "butter":  {"price": 2.00, "size": 250,  "unit": "g"},
            "eggs":    {"price": 2.00, "size": 12,   "unit": "count"},
            "vanilla": {"price": 3.00, "size": 50,   "unit": "ml"}
        },
        "buttercream": {
            "butter":      {"price": 2.00, "size": 250,  "unit": "g"},
            "icing_sugar": {"price": 1.50, "size": 1000, "unit": "g"},
            "vanilla":     {"price": 3.00, "size": 50,   "unit": "ml"},
            "milk":        {"price": 1.00, "size": 1000, "unit": "ml"}
        }
    }
    return load_json(PRICES_FILE, default)


def save_prices(prices: dict):
    save_json(PRICES_FILE, prices)


def load_buttercream_misc():
    data = load_json(BUTTERCREAM_MISC_FILE, [])
    if not isinstance(data, list):
        data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "name": item.get("name", "Unnamed item"),
            "price": float(item.get("price", 0.0)),
            "size": float(item.get("size", 0.0)),
            "unit": item.get("unit", "g")
        })
    return cleaned


def save_buttercream_misc(items):
    save_json(BUTTERCREAM_MISC_FILE, items)


def load_misc():
    data = load_json(MISC_FILE, [])
    if not isinstance(data, list):
        data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "name": item.get("name", "Unnamed item"),
            "price": float(item.get("price", 0.0)),
            "size": float(item.get("size", 0.0)),
            "unit": item.get("unit", "g")
        })
    return cleaned


def save_misc(items):
    save_json(MISC_FILE, items)


# ---------- Cost helpers ----------

def get_cost_for_ingredient(key, scaled_amount, prices_section):
    info = prices_section.get(key)
    if not info:
        return None

    price = info.get("price")
    size = info.get("size")
    unit = info.get("unit", "g")

    if price is None or not size:
        return None

    return scaled_amount * (price / size)


def get_cost_from_misc_amount(amount_used, misc_item):
    price = misc_item.get("price")
    size = misc_item.get("size")
    if not price or not size:
        return None
    return amount_used * (price / size)


# ---------- Streamlit config ----------

st.set_page_config(
    page_title="L&N CupCakes",
    page_icon="🧁",
    layout="centered"
)

st.title("🧁 L&N CupCakes")
st.caption("Cupcake & buttercream batch scaler and cost calculator")


# ---------- Shared state ----------

prices = load_prices()
buttercream_misc_items = load_buttercream_misc()
misc_items = load_misc()

batch_size = st.sidebar.selectbox(
    "Batch size (cupcakes)",
    options=[12, 24, 36, 48, 60],
    index=0
)
multiplier = batch_size / 12

page = st.sidebar.radio(
    "Navigation",
    ["Cupcake", "Buttercream", "Misc", "Total Cost", "Settings"]
)

for key in [
    "cupcake_subtotal",
    "buttercream_subtotal",
    "buttercream_misc_subtotal",
    "misc_subtotal",
]:
    if key not in st.session_state:
        st.session_state[key] = 0.0
# ---------- Page: Cupcake ----------

if page == "Cupcake":
    st.subheader("Cupcake sponge")

    rows = []
    total_cost = 0.0

    cupcake_prices = prices.get("cupcake", {})

    for key, meta in CUPCAKE_RECIPE.items():
        label = meta["label"]
        base_amount = meta["amount"]
        unit = meta["unit"]
        scaled_amount = base_amount * multiplier

        # tsp vanilla not costed
        if unit == "tsp":
            cost = None
        else:
            cost = get_cost_for_ingredient(key, scaled_amount, cupcake_prices)

        if cost is None:
            cost_display = "—"
        else:
            cost_display = f"£{cost:.2f}"
            total_cost += cost

        rows.append({
            "Ingredient": label,
            "Amount": f"{scaled_amount:.2f} {unit}",
            "Cost": cost_display
        })

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.metric("Cupcake subtotal", f"£{total_cost:.2f}")
    st.session_state["cupcake_subtotal"] = total_cost


# ---------- Page: Buttercream ----------

elif page == "Buttercream":
    st.subheader("Buttercream")

    rows = []
    total_cost = 0.0

    buttercream_prices = prices.get("buttercream", {})

    for key, meta in BUTTERCREAM_RECIPE.items():
        label = meta["label"]
        base_amount = meta["amount"]
        unit = meta["unit"]
        scaled_amount = base_amount * multiplier

        # tbsp/tsp not costed
        if unit in ["tbsp", "tsp"]:
            cost = None
        else:
            cost = get_cost_for_ingredient(key, scaled_amount, buttercream_prices)

        if cost is None:
            cost_display = "—"
        else:
            cost_display = f"£{cost:.2f}"
            total_cost += cost

        rows.append({
            "Ingredient": label,
            "Amount": f"{scaled_amount:.2f} {unit}",
            "Cost": cost_display
        })

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("### Buttercream misc (flavour add-ins)")

    misc_total = 0.0

    for i, item in enumerate(buttercream_misc_items):
        name = item.get("name", f"Item {i+1}")
        size = item.get("size", 0)
        unit = item.get("unit", "g")
        price = item.get("price", 0.0)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{name}** ({size}{unit} @ £{price:.2f})")
        with col2:
            amount_used = st.number_input(
                f"Amount used ({unit}) – {name}",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key=f"bc_misc_amount_{i}"
            )
        with col3:
            cost = get_cost_from_misc_amount(amount_used, item)
            if cost is not None:
                misc_total += cost
                st.markdown(f"Cost: **£{cost:.2f}**")
            else:
                st.markdown("Cost: —")

    st.metric("Buttercream base subtotal", f"£{total_cost:.2f}")
    st.metric("Buttercream misc subtotal", f"£{misc_total:.2f}")

    st.session_state["buttercream_subtotal"] = total_cost
    st.session_state["buttercream_misc_subtotal"] = misc_total


# ---------- Page: Misc ----------

elif page == "Misc":
    st.subheader("Miscellaneous costs")

    misc_total = 0.0

    for i, item in enumerate(misc_items):
        name = item.get("name", f"Item {i+1}")
        size = item.get("size", 0)
        unit = item.get("unit", "g")
        price = item.get("price", 0.0)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{name}** ({size}{unit} @ £{price:.2f})")
        with col2:
            amount_used = st.number_input(
                f"Amount used ({unit}) – {name}",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key=f"misc_amount_{i}"
            )
        with col3:
            cost = get_cost_from_misc_amount(amount_used, item)
            if cost is not None:
                misc_total += cost
                st.markdown(f"Cost: **£{cost:.2f}**")
            else:
                st.markdown("Cost: —")

    st.metric("Misc subtotal", f"£{misc_total:.2f}")
    st.session_state["misc_subtotal"] = misc_total


# ---------- Page: Total Cost ----------

elif page == "Total Cost":
    st.subheader("Total cost summary")

    cupcake_sub = st.session_state["cupcake_subtotal"]
    buttercream_sub = st.session_state["buttercream_subtotal"]
    buttercream_misc_sub = st.session_state["buttercream_misc_subtotal"]
    misc_sub = st.session_state["misc_subtotal"]

    total = cupcake_sub + buttercream_sub + buttercream_misc_sub + misc_sub
    cost_per_cupcake = total / batch_size if batch_size else 0

    rows = [
        {"Section": "Cupcakes", "Subtotal": f"£{cupcake_sub:.2f}"},
        {"Section": "Buttercream", "Subtotal": f"£{buttercream_sub:.2f}"},
        {"Section": "Buttercream misc", "Subtotal": f"£{buttercream_misc_sub:.2f}"},
        {"Section": "Misc", "Subtotal": f"£{misc_sub:.2f}"},
        {"Section": "Total", "Subtotal": f"£{total:.2f}"}
    ]

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.metric("Grand total", f"£{total:.2f}")
    st.metric("Cost per cupcake", f"£{cost_per_cupcake:.2f}")
# ---------- Page: Settings (Function Version) ----------

def settings_page():
    st.subheader("Settings")

    updated_prices = prices.copy()
    cupcake_prices = updated_prices.get("cupcake", {})
    buttercream_prices = updated_prices.get("buttercream", {})

    # ------------------------------
    # CUPCAKE INGREDIENT PRICES
    # ------------------------------
    st.markdown("### Cupcake ingredient prices")

    for key, meta in CUPCAKE_RECIPE.items():
        label = meta["label"]
        existing = cupcake_prices.get(key, {})
        default_unit = existing.get("unit", meta["unit"])

        col1, col2, col3 = st.columns(3)

        with col1:
            price = st.number_input(
                f"{label} price (£)",
                min_value=0.0,
                value=float(existing.get("price", 0.0)),
                step=0.10,
                key=f"cupcake_price_{key}"
            )

        with col2:
            size = st.number_input(
                f"{label} package size",
                min_value=0.0,
                value=float(existing.get("size", 0.0)),
                step=10.0,
                key=f"cupcake_size_{key}"
            )

        with col3:
            unit = st.selectbox(
                f"{label} unit",
                ["g", "ml", "count"],
                index=["g", "ml", "count"].index(default_unit),
                key=f"cupcake_unit_{key}"
            )

        cupcake_prices[key] = {"price": price, "size": size, "unit": unit}

    updated_prices["cupcake"] = cupcake_prices

    # ------------------------------
    # BUTTERCREAM INGREDIENT PRICES
    # ------------------------------
    st.markdown("### Buttercream ingredient prices")

    for key, meta in BUTTERCREAM_RECIPE.items():
        label = meta["label"]
        existing = buttercream_prices.get(key, {})
        default_unit = existing.get("unit", meta["unit"])

        col1, col2, col3 = st.columns(3)

        with col1:
            price = st.number_input(
                f"{label} price (£)",
                min_value=0.0,
                value=float(existing.get("price", 0.0)),
                step=0.10,
                key=f"buttercream_price_{key}"
            )

        with col2:
            size = st.number_input(
                f"{label} package size",
                min_value=0.0,
                value=float(existing.get("size", 0.0)),
                step=10.0,
                key=f"buttercream_size_{key}"
            )

        with col3:
            unit = st.selectbox(
                f"{label} unit",
                ["g", "ml", "count"],
                index=["g", "ml", "count"].index(default_unit),
                key=f"buttercream_unit_{key}"
            )

        buttercream_prices[key] = {"price": price, "size": size, "unit": unit}

    updated_prices["buttercream"] = buttercream_prices

    # ------------------------------
    # BUTTERCREAM MISC ITEMS
    # ------------------------------
    st.markdown("### Buttercream misc items")

    bc_misc = buttercream_misc_items.copy()

    for i, item in enumerate(bc_misc):
        name = item["name"]
        price = item["price"]
        size = item["size"]
        unit = item["unit"]

        st.markdown(f"**Item {i+1}: {name}**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            name = st.text_input("Name", value=name, key=f"bc_misc_name_{i}")

        with col2:
            price = st.number_input(
                "Price (£)",
                min_value=0.0,
                value=price,
                step=0.10,
                key=f"bc_misc_price_{i}"
            )

        with col3:
            size = st.number_input(
                "Size",
                min_value=0.0,
                value=size,
                step=10.0,
                key=f"bc_misc_size_{i}"
            )

        with col4:
            unit = st.selectbox(
                "Unit",
                ["g", "ml", "count"],
                index=["g", "ml", "count"].index(unit),
                key=f"bc_misc_unit_{i}"
            )

        bc_misc[i] = {"name": name, "price": price, "size": size, "unit": unit}

        # DELETE BUTTON
        if st.button(f"Delete buttercream misc item {i+1}", key=f"bc_misc_delete_{i}"):
            bc_misc.pop(i)
            save_buttercream_misc(bc_misc)
            st.experimental_rerun()
            return

    # ADD NEW BUTTERCREAM MISC ITEM
    if st.button("Add buttercream misc item"):
        bc_misc.append({"name": "New item", "price": 0.0, "size": 0.0, "unit": "g"})
        save_buttercream_misc(bc_misc)
        st.experimental_rerun()
        return

    # ------------------------------
    # GENERAL MISC ITEMS
    # ------------------------------
    st.markdown("### General misc items")

    misc = misc_items.copy()

    for i, item in enumerate(misc):
        name = item["name"]
        price = item["price"]
        size = item["size"]
        unit = item["unit"]

        st.markdown(f"**Item {i+1}: {name}**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            name = st.text_input("Name", value=name, key=f"misc_name_{i}")

        with col2:
            price = st.number_input(
                "Price (£)",
                min_value=0.0,
                value=price,
                step=0.10,
                key=f"misc_price_{i}"
            )

        with col3:
            size = st.number_input(
                "Size",
                min_value=0.0,
                value=size,
                step=10.0,
                key=f"misc_size_{i}"
            )

        with col4:
            unit = st.selectbox(
                "Unit",
                ["g", "ml", "count"],
                index=["g", "ml", "count"].index(unit),
                key=f"misc_unit_{i}"
            )

        misc[i] = {"name": name, "price": price, "size": size, "unit": unit}

        # DELETE BUTTON
        if st.button(f"Delete misc item {i+1}", key=f"misc_delete_{i}"):
            misc.pop(i)
            save_misc(misc)
            st.experimental_rerun()
            return

    # ADD NEW GENERAL MISC ITEM
    if st.button("Add misc item"):
        misc.append({"name": "New item", "price": 0.0, "size": 0.0, "unit": "g"})
        save_misc(misc)
        st.experimental_rerun()
        return

    # ------------------------------
    # SAVE ALL SETTINGS
    # ------------------------------
    if st.button("💾 Save all settings"):
        save_prices(updated_prices)
        save_buttercream_misc(bc_misc)
        save_misc(misc)
        st.success("Settings saved.")


# Call the function when needed
if page == "Settings":
    settings_page()

