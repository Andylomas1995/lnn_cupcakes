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
    # scaled from your 24-cup batch to 12
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
    with open(path) as f:
        return json.load(f)


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
    return load_json(BUTTERCREAM_MISC_FILE, [])


def save_buttercream_misc(items):
    save_json(BUTTERCREAM_MISC_FILE, items)


def load_misc():
    return load_json(MISC_FILE, [])


def save_misc(items):
    save_json(MISC_FILE, items)


# ---------- Cost helpers ----------

def get_cost_for_ingredient(key, scaled_amount, prices_section):
    """Return cost in £ for a given ingredient amount using a section of prices."""
    info = prices_section.get(key)
    if not info:
        return None

    price = info.get("price")
    size = info.get("size")
    unit = info.get("unit", "g")

    if price is None or not size:
        return None

    # eggs by count, others by weight/volume
    if unit == "count":
        cost_per_unit = price / size
        return scaled_amount * cost_per_unit
    else:
        cost_per_unit = price / size
        return scaled_amount * cost_per_unit


def get_cost_from_misc_amount(amount_used, misc_item):
    """amount_used in same unit as misc_item size."""
    price = misc_item.get("price")
    size = misc_item.get("size")
    if not price or not size:
        return None
    cost_per_unit = price / size
    return amount_used * cost_per_unit


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

# Batch size selection (shared across pages)
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

# To accumulate subtotals across pages
if "cupcake_subtotal" not in st.session_state:
    st.session_state["cupcake_subtotal"] = 0.0
if "buttercream_subtotal" not in st.session_state:
    st.session_state["buttercream_subtotal"] = 0.0
if "buttercream_misc_subtotal" not in st.session_state:
    st.session_state["buttercream_misc_subtotal"] = 0.0
if "misc_subtotal" not in st.session_state:
    st.session_state["misc_subtotal"] = 0.0


# ---------- Page: Cupcake ----------

if page == "Cupcake":
    st.subheader("Cupcake sponge")

    st.markdown(f"Base recipe is for **12 cupcakes**. Multiplier: `{multiplier}x`")

    rows = []
    total_cost = 0.0
    missing_cost = False

    cupcake_prices = prices.get("cupcake", {})

    for key, meta in CUPCAKE_RECIPE.items():
        label = meta["label"]
        base_amount = meta["amount"]
        unit = meta["unit"]

        scaled_amount = base_amount * multiplier

        # tsp vanilla not costed (tiny)
        if unit == "tsp":
            cost = None
        else:
            cost = get_cost_for_ingredient(key, scaled_amount, cupcake_prices)

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
        st.metric("Cupcake subtotal", f"£{total_cost:.2f}")
    with col2:
        cost_per_cupcake = total_cost / batch_size if batch_size else 0
        st.metric("Cost per cupcake (sponge only)", f"£{cost_per_cupcake:.2f}")

    if missing_cost:
        st.info("Some ingredients are missing cost data or not costed (e.g. vanilla tsp). Update prices in Settings.")

    st.session_state["cupcake_subtotal"] = total_cost


# ---------- Page: Buttercream ----------

elif page == "Buttercream":
    st.subheader("Buttercream")

    st.markdown(f"Base buttercream recipe is for **12 cupcakes**. Multiplier: `{multiplier}x`")

    rows = []
    total_cost = 0.0
    missing_cost = False

    buttercream_prices = prices.get("buttercream", {})

    for key, meta in BUTTERCREAM_RECIPE.items():
        label = meta["label"]
        base_amount = meta["amount"]
        unit = meta["unit"]

        scaled_amount = base_amount * multiplier

        # tbsp/tsp not costed by default
        if unit in ["tbsp", "tsp"]:
            cost = None
        else:
            cost = get_cost_for_ingredient(key, scaled_amount, buttercream_prices)

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
    st.markdown("### Base buttercream ingredients")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### Buttercream misc (flavour add-ins)")

    misc_rows = []
    misc_total = 0.0

    if buttercream_misc_items:
        for i, item in enumerate(buttercream_misc_items):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{item['name']}** ({item['size']}{item['unit']} @ £{item['price']:.2f})")
            with col2:
                amount_used = st.number_input(
                    f"Amount used ({item['unit']}) – {item['name']}",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"bc_misc_amount_{i}"
                )
            with col3:
                cost = get_cost_from_misc_amount(amount_used, item)
                if cost is None:
                    cost_display = "—"
                else:
                    cost_display = f"£{cost:.2f}"
                    misc_total += cost
                st.markdown(f"Cost: **{cost_display}**")

            misc_rows.append({
                "Item": item["name"],
                "Amount used": f"{st.session_state.get(f'bc_misc_amount_{i}', 0.0)} {item['unit']}",
                "Cost": cost_display
            })
    else:
        st.info("No buttercream misc items defined yet. Add them in Settings.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Buttercream base subtotal", f"£{total_cost:.2f}")
    with col2:
        st.metric("Buttercream misc subtotal", f"£{misc_total:.2f}")

    st.session_state["buttercream_subtotal"] = total_cost
    st.session_state["buttercream_misc_subtotal"] = misc_total


# ---------- Page: Misc (general) ----------

elif page == "Misc":
    st.subheader("Miscellaneous costs")

    st.markdown("These are general extras like cases, boxes, sprinkles, electricity, labour, etc.")

    if misc_items:
        rows = []
        misc_total = 0.0
        for i, item in enumerate(misc_items):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{item['name']}** ({item['size']}{item['unit']} @ £{item['price']:.2f})")
            with col2:
                amount_used = st.number_input(
                    f"Amount used ({item['unit']}) – {item['name']}",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"misc_amount_{i}"
                )
            with col3:
                cost = get_cost_from_misc_amount(amount_used, item)
                if cost is None:
                    cost_display = "—"
                else:
                    cost_display = f"£{cost:.2f}"
                    misc_total += cost
                st.markdown(f"Cost: **{cost_display}**")

            rows.append({
                "Item": item["name"],
                "Amount used": f"{st.session_state.get(f'misc_amount_{i}', 0.0)} {item['unit']}",
                "Cost": cost_display
            })

        st.markdown("---")
        st.metric("Misc subtotal", f"£{misc_total:.2f}")
        st.session_state["misc_subtotal"] = misc_total
    else:
        st.info("No misc items defined yet. Add them in Settings.")


# ---------- Page: Total Cost ----------

elif page == "Total Cost":
    st.subheader("Total cost summary")

    cupcake_sub = st.session_state.get("cupcake_subtotal", 0.0)
    buttercream_sub = st.session_state.get("buttercream_subtotal", 0.0)
    buttercream_misc_sub = st.session_state.get("buttercream_misc_subtotal", 0.0)
    misc_sub = st.session_state.get("misc_subtotal", 0.0)

    total = cupcake_sub + buttercream_sub + buttercream_misc_sub + misc_sub
    cost_per_cupcake = total / batch_size if batch_size else 0

    rows = [
        {"Section": "Cupcakes", "Subtotal": f"£{cupcake_sub:.2f}"},
        {"Section": "Buttercream", "Subtotal": f"£{buttercream_sub:.2f}"},
        {"Section": "Buttercream misc", "Subtotal": f"£{buttercream_misc_sub:.2f}"},
        {"Section": "Misc", "Subtotal": f"£{misc_sub:.2f}"},
        {"Section": "Total", "Subtotal": f"£{total:.2f}"}
    ]
    df = pd.DataFrame(rows)

    st.markdown("### Breakdown")
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Grand total", f"£{total:.2f}")
    with col2:
        st.metric("Cost per cupcake", f"£{cost_per_cupcake:.2f}")


# ---------- Page: Settings ----------

elif page == "Settings":
    st.subheader("Settings")

    st.markdown("### 1. Cupcake ingredient prices")

    updated_prices = prices.copy()
    cupcake_prices = updated_prices.get("cupcake", {})
    buttercream_prices = updated_prices.get("buttercream", {})

    # Cupcake prices
    for key, meta in CUPCAKE_RECIPE.items():
        st.markdown(f"#### {meta['label']} (Cupcake)")
        existing = cupcake_prices.get(key, {})
        default_unit = "count" if meta["unit"] == "count" else "g"

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            price = st.number_input(
                f"Price (£) – {meta['label']} (cupcake)",
                min_value=0.0,
                value=float(existing.get("price", 0.0)),
                step=0.10,
                key=f"cupcake_{key}_price"
            )
        with col2:
            size = st.number_input(
                f"Package size ({default_unit}) – {meta['label']} (cupcake)",
                min_value=0.0,
                value=float(existing.get("size", 0.0)),
                step=10.0 if default_unit != "count" else 1.0,
                key=f"cupcake_{key}_size"
            )
        with col3:
            unit = st.selectbox(
                "Unit",
                options=["g", "ml", "count"],
                index=["g", "ml", "count"].index(existing.get("unit", default_unit)),
                key=f"cupcake_{key}_unit"
            )

        cupcake_prices[key] = {
            "price": price,
            "size": size,
            "unit": unit
        }

        st.markdown("---")

    updated_prices["cupcake"] = cupcake_prices

    st.markdown("### 2. Buttercream ingredient prices")

    for key, meta in BUTTERCREAM_RECIPE.items():
        st.markdown(f"#### {meta['label']} (Buttercream)")
        existing = buttercream_prices.get(key, {})
        default_unit = "g" if meta["unit"] in ["g", "tbsp", "tsp"] else "ml"

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            price = st.number_input(
                f"Price (£) – {meta['label']} (buttercream)",
                min_value=0.0,
                value=float(existing.get("price", 0.0)),
                step=0.10,
                key=f"buttercream_{key}_price"
            )
        with col2:
            size = st.number_input(
                f"Package size ({default_unit}) – {meta['label']} (buttercream)",
                min_value=0.0,
                value=float(existing.get("size", 0.0)),
                step=10.0,
                key=f"buttercream_{key}_size"
            )
        with col3:
            unit = st.selectbox(
                "Unit",
                options=["g", "ml", "count"],
                index=["g", "ml", "count"].index(existing.get("unit", default_unit)),
                key=f"buttercream_{key}_unit"
            )

        buttercream_prices[key] = {
            "price": price,
            "size": size,
            "unit": unit
        }

        st.markdown("---")

    updated_prices["buttercream"] = buttercream_prices

    st.markdown("### 3. Buttercream misc items")

    bc_misc = buttercream_misc_items.copy()

    if bc_misc:
        for i, item in enumerate(bc_misc):
            st.markdown(f"**Item {i+1}: {item['name']}**")
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                name = st.text_input(
                    "Name",
                    value=item["name"],
                    key=f"bc_misc_name_{i}"
                )
            with col2:
                price = st.number_input(
                    "Price (£)",
                    min_value=0.0,
                    value=float(item["price"]),
                    step=0.10,
                    key=f"bc_misc_price_{i}"
                )
            with col3:
                size = st.number_input(
                    "Package size",
                    min_value=0.0,
                    value=float(item["size"]),
                    step=10.0,
                    key=f"bc_misc_size_{i}"
                )
            with col4:
                unit = st.selectbox(
                    "Unit",
                    options=["g", "ml", "count"],
                    index=["g", "ml", "count"].index(item.get("unit", "g")),
                    key=f"bc_misc_unit_{i}"
                )

            bc_misc[i] = {
                "name": name,
                "price": price,
                "size": size,
                "unit": unit
            }

            if st.button(f"Delete buttercream misc item {i+1}", key=f"bc_misc_delete_{i}"):
                bc_misc.pop(i)
                save_buttercream_misc(bc_misc)
                st.experimental_rerun()

            st.markdown("---")
    else:
        st.info("No buttercream misc items yet.")

    if st.button("Add buttercream misc item"):
        bc_misc.append({
            "name": "New item",
            "price": 0.0,
            "size": 0.0,
            "unit": "g"
        })

    st.markdown("---")
    st.markdown("### 4. General misc items")

    misc = misc_items.copy()

    if misc:
        for i, item in enumerate(misc):
            st.markdown(f"**Item {i+1}: {item['name']}**")
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                name = st.text_input(
                    "Name",
                    value=item["name"],
                    key=f"misc_name_{i}"
                )
            with col2:
                price = st.number_input(
                    "Price (£)",
                    min_value=0.0,
                    value=float(item["price"]),
                    step=0.10,
                    key=f"misc_price_{i}"
                )
            with col3:
                size = st.number_input(
                    "Package size",
                    min_value=0.0,
                    value=float(item["size"]),
                    step=10.0,
                    key=f"misc_size_{i}"
                )
            with col4:
                unit = st.selectbox(
                    "Unit",
                    options=["g", "ml", "count"],
                    index=["g", "ml", "count"].index(item.get("unit", "g")),
                    key=f"misc_unit_{i}"
                )

            misc[i] = {
                "name": name,
                "price": price,
                "size": size,
                "unit": unit
            }

            if st.button(f"Delete misc item {i+1}", key=f"misc_delete_{i}"):
                misc.pop(i)
                save_misc(misc)
                st.experimental_rerun()

            st.markdown("---")
    else:
        st.info("No misc items yet.")

    if st.button("Add misc item"):
        misc.append({
            "name": "New item",
            "price": 0.0,
            "size": 0.0,
            "unit": "g"
        })

    # Save all settings
    if st.button("💾 Save all settings"):
        save_prices(updated_prices)
        save_buttercream_misc(bc_misc)
        save_misc(misc)
        st.success("Settings saved.")
