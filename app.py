import json
from pathlib import Path
from datetime import datetime, time

import pandas as pd
import streamlit as st
import requests

# ---------- Constants ----------

ADMIN_PASSWORD = "lncupcakes1922"

EMAILJS_SERVICE_ID = "service_hprefxv"
EMAILJS_TEMPLATE_ID = "template_5z7kfjg"
EMAILJS_PUBLIC_KEY = "4UiWwc89li7cpo0gr"
ORDER_TARGET_EMAIL = "andylomas79@gmail.com"
EMAIL_SUBJECT = "New Customer Order Received"

# ---------- Paths ----------

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PRICES_FILE = DATA_DIR / "prices.json"
BUTTERCREAM_MISC_FILE = DATA_DIR / "buttercream_misc.json"
MISC_FILE = DATA_DIR / "misc.json"
ORDERS_FILE = DATA_DIR / "orders.json"

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

# ---------- Customer cupcake menu (per 6) ----------

CUSTOMER_CUPCAKES = [
    {"name": "Biscoff", "price_per_6": 12.0},
    {"name": "Vanilla", "price_per_6": 10.0},
    {"name": "Chocolate", "price_per_6": 10.0},
    {"name": "Nutella", "price_per_6": 12.0},
]

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

def load_orders():
    data = load_json(ORDERS_FILE, [])
    if not isinstance(data, list):
        data = []
    return data

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

# ---------- Cost helpers ----------

def get_cost_for_ingredient(key, scaled_amount, prices_section):
    info = prices_section.get(key)
    if not info:
        return None
    price = info.get("price")
    size = info.get("size")
    if not price or not size:
        return None
    return scaled_amount * (price / size)

def get_cost_from_misc_amount(amount_used, misc_item):
    price = misc_item.get("price")
    size = misc_item.get("size")
    if not price or not size:
        return None
    return amount_used * (price / size)

# ---------- Email helper (NEW: uses order_summary) ----------

def send_order_email(order_record, order_summary):
    url = "https://api.emailjs.com/api/v1.0/email/send"

    template_params = {
        "to_email": ORDER_TARGET_EMAIL,
        "subject": EMAIL_SUBJECT,
        "customer_name": order_record["name"],
        "contact": order_record["contact"],
        "pickup_date": order_record["pickup_date"],
        "pickup_time": order_record["pickup_time"],
        "notes": order_record["notes"] or "None",
        "order_summary": order_summary,
        "total": f"{order_record['total']:.2f}",
    }

    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_PUBLIC_KEY,
        "template_params": template_params,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True, "Email sent successfully."
        else:
            return False, f"Email failed with status {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Email error: {e}"

# ---------- Streamlit config ----------

st.set_page_config(
    page_title="L&N CupCakes",
    page_icon="🧁",
    layout="centered"
)

# ---------- Shared state ----------

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

if "basket" not in st.session_state:
    st.session_state["basket"] = []

if "orders_cache" not in st.session_state:
    st.session_state["orders_cache"] = load_orders()

prices = load_prices()
buttercream_misc_items = load_buttercream_misc()
misc_items = load_misc()

for key in [
    "cupcake_subtotal",
    "buttercream_subtotal",
    "buttercream_misc_subtotal",
    "misc_subtotal",
]:
    if key not in st.session_state:
        st.session_state[key] = 0.0

# ---------- Admin login popover ----------

def show_admin_login_inline():
    with st.popover("Admin Login", use_container_width=False):
        st.markdown("### Admin login")
        pwd = st.text_input("Password", type="password", key="admin_pwd")
        if st.button("Log in", key="admin_login_btn"):
            if pwd == ADMIN_PASSWORD:
                st.session_state["is_admin"] = True
                st.success("Admin mode active.")
                st.rerun()
            else:
                st.error("Incorrect password.")

# ---------- Top bar ----------

col_title, col_admin = st.columns([4, 1])
with col_title:
    st.title("🧁 L&N CupCakes")
    st.caption("Customer ordering + bakery costing")
with col_admin:
    if st.session_state["is_admin"]:
        st.markdown("<div style='text-align:right; color: green;'>Admin</div>", unsafe_allow_html=True)
    else:
        show_admin_login_inline()

# ---------- Navigation (dynamic) ----------

if st.session_state["is_admin"]:
    pages = [
        "Home",
        "Order Cupcakes",
        "Basket",
        "Checkout",
        "Cupcake",
        "Buttercream",
        "Misc",
        "Total Cost",
        "View Orders",
        "Settings",
    ]
else:
    pages = [
        "Home",
        "Order Cupcakes",
        "Basket",
        "Checkout",
    ]

page = st.sidebar.radio("Navigation", pages)

# ---------- Batch size (admin only) ----------

if st.session_state["is_admin"]:
    batch_size = st.sidebar.selectbox(
        "Batch size (cupcakes) for costing",
        options=[12, 24, 36, 48, 60],
        index=0
    )
    multiplier = batch_size / 12
else:
    multiplier = 1  # unused in customer mode

# ---------- Page: Home ----------

if page == "Home":
    st.subheader("Welcome")
    st.write(
        "Use this app to **order cupcakes** for collection. "
        "Staff can log in (top right) to access costing tools."
    )

    st.markdown("### How to order")
    st.markdown(
        """
1. Go to **Order Cupcakes**  
2. Choose your flavours  
3. Add them to your basket  
4. Review your basket  
5. Checkout with your details  
6. Pay on collection  
        """
    )
# ---------- Page: Order Cupcakes (customer) ----------

elif page == "Order Cupcakes":
    st.subheader("Order cupcakes")

    st.markdown("### Standard flavours")
    for i, item in enumerate(CUSTOMER_CUPCAKES):
        name = item["name"]
        price_per_6 = item["price_per_6"]

        st.markdown(f"**{name}** — £{price_per_6:.2f} per 6")
        cols = st.columns([1, 1])
        with cols[0]:
            boxes = st.number_input(
                f"Boxes of 6 – {name}",
                min_value=0,
                max_value=20,
                value=0,
                step=1,
                key=f"order_boxes_{i}"
            )
        with cols[1]:
            if st.button(f"Add {name}", key=f"add_flavour_{i}"):
                if boxes > 0:
                    qty_cupcakes = boxes * 6
                    total_price = boxes * price_per_6
                    st.session_state["basket"].append({
                        "name": name,
                        "qty": qty_cupcakes,
                        "price_per_6": price_per_6,
                        "boxes": boxes,
                        "total_price": total_price,
                    })
                    st.success(f"Added {boxes} box(es) of {name} to basket.")
                else:
                    st.warning("Please select at least 1 box.")

    st.markdown("### Custom flavour")
    custom_name = st.text_input("Custom flavour name")
    custom_price_per_6 = st.number_input(
        "Price per 6 (custom)",
        min_value=0.0,
        value=12.0,
        step=0.5
    )
    custom_boxes = st.number_input(
        "Boxes of 6 – custom",
        min_value=0,
        max_value=20,
        value=0,
        step=1
    )
    if st.button("Add custom flavour"):
        if custom_name.strip() and custom_boxes > 0 and custom_price_per_6 > 0:
            qty_cupcakes = custom_boxes * 6
            total_price = custom_boxes * custom_price_per_6
            st.session_state["basket"].append({
                "name": custom_name.strip(),
                "qty": qty_cupcakes,
                "price_per_6": custom_price_per_6,
                "boxes": custom_boxes,
                "total_price": total_price,
            })
            st.success(f"Added {custom_boxes} box(es) of {custom_name} to basket.")
        else:
            st.warning("Please enter a name, price, and at least 1 box.")

# ---------- Page: Basket (customer) ----------

elif page == "Basket":
    st.subheader("Your basket")

    basket = st.session_state["basket"]
    if not basket:
        st.info("Your basket is empty. Go to 'Order Cupcakes' to add items.")
    else:
        rows = []
        total = 0.0
        for idx, item in enumerate(basket):
            rows.append({
                "Flavour": item["name"],
                "Boxes of 6": item["boxes"],
                "Cupcakes": item["qty"],
                "Price per 6": f"£{item['price_per_6']:.2f}",
                "Line total": f"£{item['total_price']:.2f}",
            })
            total += item["total_price"]

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.metric("Basket total", f"£{total:.2f}")

        for idx, item in enumerate(basket):
            if st.button(f"Remove {item['name']} (row {idx+1})", key=f"remove_{idx}"):
                st.session_state["basket"].pop(idx)
                st.rerun()

# ---------- Page: Checkout (customer, with order_summary email) ----------

elif page == "Checkout":
    st.subheader("Checkout — payment on collection")

    basket = st.session_state["basket"]
    if not basket:
        st.info("Your basket is empty. Go to 'Order Cupcakes' to add items.")
    else:
        total = sum(item["total_price"] for item in basket)
        st.metric("Order total", f"£{total:.2f}")

        st.markdown("### Your details")
        name = st.text_input("Your name")
        contact = st.text_input("Contact (phone or email)")
        pickup_date = st.date_input("Pickup date")
        pickup_time = st.time_input("Pickup time", value=time(12, 0))
        notes = st.text_area("Notes (allergies, messages on box, etc.)", height=80)

        st.markdown("### Order summary")
        rows = []
        for item in basket:
            rows.append({
                "Flavour": item["name"],
                "Boxes of 6": item["boxes"],
                "Cupcakes": item["qty"],
                "Line total": f"£{item['total_price']:.2f}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        if st.button("Place order (pay on collection)"):
            if not name.strip() or not contact.strip():
                st.warning("Please enter your name and contact details.")
            else:

                # Build clean order summary for EmailJS
                order_summary = ""
                for item in basket:
                    order_summary += (
                        f"• {item['boxes']} box(es) of {item['name']} "
                        f"({item['qty']} cupcakes) — £{item['total_price']:.2f}\n"
                    )

                order_record = {
                    "timestamp": datetime.now().isoformat(),
                    "name": name.strip(),
                    "contact": contact.strip(),
                    "pickup_date": pickup_date.isoformat(),
                    "pickup_time": pickup_time.isoformat(),
                    "notes": notes.strip(),
                    "items": basket,
                    "total": total,
                }

                # Save locally
                all_orders = load_orders()
                all_orders.append(order_record)
                save_orders(all_orders)
                st.session_state["orders_cache"] = all_orders

                # Send email with order_summary
                success, msg = send_order_email(order_record, order_summary)
                if success:
                    st.success("Order placed and email sent! Payment on collection. Thank you.")
                else:
                    st.warning(f"Order saved, but email failed: {msg}")

                st.session_state["basket"] = []
                st.balloons()

# ---------- Admin: Cupcake costing ----------

elif page == "Cupcake":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        st.subheader("Cupcake sponge costing")

        rows = []
        total_cost = 0.0
        cupcake_prices = prices.get("cupcake", {})

        for key, meta in CUPCAKE_RECIPE.items():
            label = meta["label"]
            base_amount = meta["amount"]
            unit = meta["unit"]
            scaled_amount = base_amount * multiplier

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

# ---------- Admin: Buttercream costing ----------

elif page == "Buttercream":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        st.subheader("Buttercream costing")

        rows = []
        total_cost = 0.0
        buttercream_prices = prices.get("buttercream", {})

        for key, meta in BUTTERCREAM_RECIPE.items():
            label = meta["label"]
            base_amount = meta["amount"]
            unit = meta["unit"]
            scaled_amount = base_amount * multiplier

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
            name = item["name"]
            size = item["size"]
            unit = item["unit"]
            price = item["price"]

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
                if cost:
                    misc_total += cost
                    st.markdown(f"Cost: **£{cost:.2f}**")
                else:
                    st.markdown("Cost: —")

        st.metric("Buttercream base subtotal", f"£{total_cost:.2f}")
        st.metric("Buttercream misc subtotal", f"£{misc_total:.2f}")

        st.session_state["buttercream_subtotal"] = total_cost
        st.session_state["buttercream_misc_subtotal"] = misc_total

# ---------- Admin: Misc costing ----------

elif page == "Misc":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        st.subheader("Miscellaneous costs")

        misc_total = 0.0

        for i, item in enumerate(misc_items):
            name = item["name"]
            size = item["size"]
            unit = item["unit"]
            price = item["price"]

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
                if cost:
                    misc_total += cost
                    st.markdown(f"Cost: **£{cost:.2f}**")
                else:
                    st.markdown("Cost: —")

        st.metric("Misc subtotal", f"£{misc_total:.2f}")
        st.session_state["misc_subtotal"] = misc_total

# ---------- Admin: Total Cost ----------

elif page == "Total Cost":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        st.subheader("Total cost summary")

        cupcake_sub = st.session_state["cupcake_subtotal"]
        buttercream_sub = st.session_state["buttercream_subtotal"]
        buttercream_misc_sub = st.session_state["buttercream_misc_subtotal"]
        misc_sub = st.session_state["misc_subtotal"]

        total = cupcake_sub + buttercream_sub + buttercream_misc_sub + misc_sub
        cost_per_cupcake = total / batch_size if st.session_state["is_admin"] and batch_size else 0

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
# ---------- Admin: View Orders ----------

elif page == "View Orders":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        st.subheader("All customer orders")

        orders = load_orders()
        if not orders:
            st.info("No orders have been placed yet.")
        else:
            rows = []
            for idx, o in enumerate(orders):
                rows.append({
                    "Index": idx,
                    "Timestamp": o.get("timestamp", ""),
                    "Name": o.get("name", ""),
                    "Contact": o.get("contact", ""),
                    "Pickup date": o.get("pickup_date", ""),
                    "Pickup time": o.get("pickup_time", ""),
                    "Total": f"£{o.get('total', 0.0):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            selected = st.number_input(
                "View order details by index",
                min_value=0,
                max_value=len(orders) - 1,
                value=0,
                step=1
            )
            order = orders[selected]
            st.markdown(f"### Order #{selected}")
            st.write(f"**Name:** {order['name']}")
            st.write(f"**Contact:** {order['contact']}")
            st.write(f"**Pickup:** {order['pickup_date']} at {order['pickup_time']}")
            st.write(f"**Notes:** {order['notes'] or '—'}")
            st.write(f"**Total:** £{order['total']:.2f}")

            st.markdown("#### Items")
            item_rows = []
            for item in order["items"]:
                item_rows.append({
                    "Flavour": item["name"],
                    "Boxes of 6": item["boxes"],
                    "Cupcakes": item["qty"],
                    "Line total": f"£{item['total_price']:.2f}",
                })
            st.dataframe(pd.DataFrame(item_rows), hide_index=True, use_container_width=True)

# ---------- Admin: Settings ----------

elif page == "Settings":
    if not st.session_state["is_admin"]:
        st.warning("Admin only.")
    else:
        settings_page()
