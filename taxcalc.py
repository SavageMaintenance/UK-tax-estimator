"""Income tax and Class 4 NI calculation for self-employed profits (England/Wales/NI).

Copyright (c) 2026 Edd Savage. MIT licence. Estimates only - not tax advice.
"""

import copy
import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "tax-estimator"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# 2025/26 rates. All band "from" figures are profit thresholds as published on gov.uk
# (e.g. higher rate from £50,270). NI applies them to profit directly; income tax
# converts them to taxable income in tax_bands_on_taxable_income().
SETTINGS_VERSION = 2

DEFAULT_SETTINGS = {
    "version": SETTINGS_VERSION,
    "tax_year": "2025/26",
    "personal_allowance": 12570,
    "taper_enabled": True,
    "taper_threshold": 100000,
    "tax_bands": [
        {"name": "Basic rate", "from": 12570, "rate": 20},
        {"name": "Higher rate", "from": 50270, "rate": 40},
        {"name": "Additional rate", "from": 125140, "rate": 45},
    ],
    "ni_bands": [
        {"name": "Class 4 main rate", "from": 12570, "rate": 6},
        {"name": "Class 4 upper rate", "from": 50270, "rate": 2},
    ],
}


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        if data.get("version") != SETTINGS_VERSION:
            # Older files stored income tax bands on taxable income; keep defaults for those.
            data.pop("tax_bands", None)
            data["version"] = SETTINGS_VERSION
        settings.update(data)
        return settings
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
    tmp.replace(SETTINGS_FILE)


def _apply_bands(amount, bands):
    """Split amount across bands (each runs from its 'from' to the next band's 'from')."""
    bands = sorted(bands, key=lambda b: b["from"])
    rows = []
    for i, band in enumerate(bands):
        lower = band["from"]
        upper = bands[i + 1]["from"] if i + 1 < len(bands) else None
        if amount <= lower:
            portion = 0.0
        else:
            portion = (min(amount, upper) if upper is not None else amount) - lower
        rows.append({
            "name": band["name"],
            "rate": band["rate"],
            "lower": lower,
            "upper": upper,
            "amount": portion,
            "due": portion * band["rate"] / 100,
        })
    return rows


def personal_allowance(profit, settings):
    pa = settings["personal_allowance"]
    if settings["taper_enabled"] and profit > settings["taper_threshold"]:
        pa = max(0.0, pa - (profit - settings["taper_threshold"]) / 2)
    return pa


def tax_bands_on_taxable_income(settings):
    """Convert gov.uk-style profit thresholds to HMRC's taxable-income thresholds.

    A threshold T means "someone with profit T starts paying this rate", so on taxable
    income it sits at T minus the allowance that person would have. With a full
    allowance £50,270 -> £37,700; at £125,140 the allowance has tapered to nil so it
    stays £125,140.
    """
    return [
        dict(b, **{"from": max(0.0, b["from"] - personal_allowance(b["from"], settings))})
        for b in settings["tax_bands"]
    ]


def calculate(profit, settings):
    profit = max(0.0, float(profit))
    pa = personal_allowance(profit, settings)
    taxable = max(0.0, profit - pa)
    tax_rows = _apply_bands(taxable, tax_bands_on_taxable_income(settings))
    # Show the published profit thresholds rather than the converted ones.
    published = sorted(b["from"] for b in settings["tax_bands"])
    for i, row in enumerate(tax_rows):
        row["lower"] = published[i]
        row["upper"] = published[i + 1] if i + 1 < len(published) else None
    ni_rows = _apply_bands(profit, settings["ni_bands"])
    income_tax = sum(r["due"] for r in tax_rows)
    ni = sum(r["due"] for r in ni_rows)
    total = income_tax + ni
    return {
        "profit": profit,
        "personal_allowance": pa,
        "taxable": taxable,
        "tax_rows": tax_rows,
        "ni_rows": ni_rows,
        "income_tax": income_tax,
        "ni": ni,
        "total": total,
        "effective_rate": (total / profit * 100) if profit else 0.0,
        "take_home": profit - total,
    }
