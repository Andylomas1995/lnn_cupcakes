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
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        # if file is corrupted, reset to default
        data = default
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
    return data


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
    # ensure it's a list of dicts
    if not isinstance(data, list):
        data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # enforce keys with safe defaults
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
    """Return cost in £ for a given ingredient amount using a section of prices."""
    info = prices_section.get(key)
    if not info:
        return None

    price = info.get("price")
    size = info.get("size")
    unit = info.get("unit", "g")

    if price is None or not size:
        return None

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
    cost_per
