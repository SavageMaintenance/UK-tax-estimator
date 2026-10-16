#!/usr/bin/env python3
"""Tax Estimator: GTK app estimating income tax + Class 4 NI on self-employed profits.

Copyright (c) 2026 Edd Savage. MIT licence. Estimates only - not tax advice.
"""

import copy
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import taxcalc  # noqa: E402


def money(value):
    return f"£{value:,.2f}"


def parse_number(text):
    text = text.replace("£", "").replace(",", "").strip()
    return float(text) if text else 0.0


RATES_URL = "https://www.gov.uk/income-tax-rates"
NI_URL = "https://www.gov.uk/self-employed-national-insurance-rates"

DISCLAIMER = (
    "This is an estimate only and is not tax or financial advice. Tax bands and rates change, "
    "usually every April. Check that the bands in Settings match the current figures on "
    f"<a href='{RATES_URL}'>gov.uk income tax rates</a> and "
    f"<a href='{NI_URL}'>self-employed NI rates</a> before relying on any figure. "
    "It assumes English, Welsh or Northern Irish rates and Class 4 NI only, and ignores Scottish rates, "
    "student loans, pension contributions, other income and reliefs."
)

CSS = b"""
.total-amount { font-size: 32px; font-weight: bold; }
.section-title { font-weight: bold; font-size: 14px; }
.dim-label { opacity: 0.7; }
"""


class EstimatePage(Gtk.Box):
    def __init__(self, app_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.app_window = app_window
        self.set_border_width(18)

        entry_row = Gtk.Box(spacing=12)
        label = Gtk.Label(label="Taxable earnings (profit) £")
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("e.g. 44996")
        self.entry.set_hexpand(True)
        self.entry.connect("changed", lambda *_: self.refresh())
        entry_row.pack_start(label, False, False, 0)
        entry_row.pack_start(self.entry, True, True, 0)
        self.pack_start(entry_row, False, False, 0)

        self.error_label = Gtk.Label(xalign=0)
        self.pack_start(self.error_label, False, False, 0)

        total_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        caption = Gtk.Label(label="Estimated tax bill (income tax + NI)", xalign=0)
        caption.get_style_context().add_class("dim-label")
        self.total_label = Gtk.Label(label=money(0), xalign=0, selectable=True)
        self.total_label.get_style_context().add_class("total-amount")
        self.summary_label = Gtk.Label(xalign=0)
        self.summary_label.get_style_context().add_class("dim-label")
        total_box.pack_start(caption, False, False, 0)
        total_box.pack_start(self.total_label, False, False, 0)
        total_box.pack_start(self.summary_label, False, False, 0)
        self.pack_start(total_box, False, False, 0)

        self.pack_start(Gtk.Separator(), False, False, 0)

        self.breakdown = Gtk.Grid(column_spacing=24, row_spacing=6)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.breakdown)
        self.pack_start(scroller, True, True, 0)

        disclaimer = Gtk.Label(xalign=0, wrap=True, use_markup=True)
        disclaimer.set_markup("<small>" + DISCLAIMER + "</small>")
        disclaimer.get_style_context().add_class("dim-label")
        self.pack_start(Gtk.Separator(), False, False, 0)
        self.pack_start(disclaimer, False, False, 0)

        self.entry.connect("activate", lambda *_: self.refresh())

    def refresh(self):
        settings = self.app_window.settings
        try:
            profit = parse_number(self.entry.get_text())
            self.error_label.set_text("")
        except ValueError:
            self.error_label.set_markup("<span foreground='#c01c28'>Please enter a number</span>")
            return

        result = taxcalc.calculate(profit, settings)
        self.total_label.set_text(money(result["total"]))
        self.summary_label.set_text(
            f"Income tax {money(result['income_tax'])}  ·  NI {money(result['ni'])}  ·  "
            f"Effective rate {result['effective_rate']:.1f}%  ·  "
            f"Take-home {money(result['take_home'])}  ·  Tax year {settings['tax_year']}"
        )

        for child in self.breakdown.get_children():
            self.breakdown.remove(child)

        row = 0

        def add_row(cells, title=False, dim=False):
            nonlocal row
            for col, text in enumerate(cells):
                lbl = Gtk.Label(label=text, xalign=0 if col == 0 else 1)
                if title:
                    lbl.get_style_context().add_class("section-title")
                if dim:
                    lbl.get_style_context().add_class("dim-label")
                self.breakdown.attach(lbl, col, row, 1, 1)
            row += 1

        add_row(["Income tax", "Band", "Rate", "Amount in band", "Due"], title=True)
        add_row(["Personal allowance", "", "0%", money(min(profit, result["personal_allowance"])), money(0)])
        for r in result["tax_rows"]:
            add_row(self._band_cells(r))
        add_row(["Total income tax", "", "", "", money(result["income_tax"])], dim=True)

        row += 1
        add_row(["National Insurance", "Band", "Rate", "Amount in band", "Due"], title=True)
        for r in result["ni_rows"]:
            add_row(self._band_cells(r))
        add_row(["Total NI", "", "", "", money(result["ni"])], dim=True)

        self.breakdown.show_all()

    @staticmethod
    def _band_cells(r):
        upper = f"£{r['upper']:,.0f}" if r["upper"] is not None else "+"
        band = f"£{r['lower']:,.0f} – {upper}" if r["upper"] is not None else f"£{r['lower']:,.0f}+"
        return [r["name"], band, f"{r['rate']:g}%", money(r["amount"]), money(r["due"])]


class BandEditor(Gtk.Box):
    """Editable table of bands: name, from (£), rate (%)."""

    def __init__(self, title, from_hint):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        heading = Gtk.Label(label=title, xalign=0)
        heading.get_style_context().add_class("section-title")
        hint = Gtk.Label(label=from_hint, xalign=0, wrap=True)
        hint.get_style_context().add_class("dim-label")
        self.pack_start(heading, False, False, 0)
        self.pack_start(hint, False, False, 0)

        self.store = Gtk.ListStore(str, str, str)
        self.view = Gtk.TreeView(model=self.store)
        for idx, (col_title, expand) in enumerate([("Name", True), ("From (£)", False), ("Rate (%)", False)]):
            renderer = Gtk.CellRendererText(editable=True)
            renderer.connect("edited", self._on_edited, idx)
            column = Gtk.TreeViewColumn(col_title, renderer, text=idx)
            column.set_expand(expand)
            column.set_min_width(110)
            self.view.append_column(column)
        frame = Gtk.Frame()
        frame.add(self.view)
        self.pack_start(frame, False, False, 0)

        buttons = Gtk.Box(spacing=6)
        add_btn = Gtk.Button(label="Add band")
        add_btn.connect("clicked", lambda *_: self.store.append(["New band", "0", "0"]))
        remove_btn = Gtk.Button(label="Remove selected")
        remove_btn.connect("clicked", self._on_remove)
        buttons.pack_start(add_btn, False, False, 0)
        buttons.pack_start(remove_btn, False, False, 0)
        self.pack_start(buttons, False, False, 0)

    def _on_edited(self, _renderer, path, text, column):
        self.store[path][column] = text

    def _on_remove(self, _btn):
        model, it = self.view.get_selection().get_selected()
        if it is not None:
            model.remove(it)

    def set_bands(self, bands):
        self.store.clear()
        for b in sorted(bands, key=lambda b: b["from"]):
            self.store.append([b["name"], f"{b['from']:g}", f"{b['rate']:g}"])

    def get_bands(self):
        bands = []
        for name, frm, rate in self.store:
            bands.append({"name": name.strip() or "Band", "from": parse_number(frm), "rate": parse_number(rate)})
        return sorted(bands, key=lambda b: b["from"])


class SettingsPage(Gtk.Box):
    def __init__(self, app_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.app_window = app_window

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_border_width(18)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(content)
        self.pack_start(scroller, True, True, 0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        self.tax_year = Gtk.Entry()
        self.allowance = Gtk.Entry()
        self.taper_enabled = Gtk.CheckButton(label="Reduce allowance by £1 for every £2 earned over the threshold")
        self.taper_threshold = Gtk.Entry()
        for r, (text, widget) in enumerate([
            ("Tax year", self.tax_year),
            ("Personal allowance (£)", self.allowance),
            ("Allowance taper", self.taper_enabled),
            ("Taper threshold (£)", self.taper_threshold),
        ]):
            grid.attach(Gtk.Label(label=text, xalign=0), 0, r, 1, 1)
            grid.attach(widget, 1, r, 1, 1)
        content.pack_start(grid, False, False, 0)

        self.tax_bands = BandEditor(
            "Income tax bands",
            "'From' is the profit at which each rate starts, as published on gov.uk "
            "(e.g. higher rate from £50,270). Profit below the first band is covered by the personal allowance.",
        )
        self.ni_bands = BandEditor(
            "National Insurance bands (Class 4)",
            "'From' is profit. Each band runs until the next band starts; profits below the first band pay no NI.",
        )
        content.pack_start(self.tax_bands, False, False, 0)
        content.pack_start(self.ni_bands, False, False, 0)

        actions = Gtk.Box(spacing=6)
        actions.set_border_width(12)
        self.status = Gtk.Label(xalign=0)
        reset_btn = Gtk.Button(label="Restore defaults")
        reset_btn.connect("clicked", self._on_reset)
        revert_btn = Gtk.Button(label="Revert")
        revert_btn.connect("clicked", lambda *_: self.load(self.app_window.settings))
        save_btn = Gtk.Button(label="Save")
        save_btn.get_style_context().add_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        actions.pack_start(self.status, True, True, 0)
        actions.pack_end(save_btn, False, False, 0)
        actions.pack_end(revert_btn, False, False, 0)
        actions.pack_end(reset_btn, False, False, 0)
        self.pack_start(Gtk.Separator(), False, False, 0)
        self.pack_start(actions, False, False, 0)

    def load(self, settings):
        self.tax_year.set_text(settings["tax_year"])
        self.allowance.set_text(f"{settings['personal_allowance']:g}")
        self.taper_enabled.set_active(settings["taper_enabled"])
        self.taper_threshold.set_text(f"{settings['taper_threshold']:g}")
        self.tax_bands.set_bands(settings["tax_bands"])
        self.ni_bands.set_bands(settings["ni_bands"])
        self.status.set_text("")

    def _on_reset(self, _btn):
        self.load(taxcalc.DEFAULT_SETTINGS)
        self.status.set_text("Defaults loaded – press Save to keep them")

    def _on_save(self, _btn):
        try:
            settings = {
                "tax_year": self.tax_year.get_text().strip(),
                "personal_allowance": parse_number(self.allowance.get_text()),
                "taper_enabled": self.taper_enabled.get_active(),
                "taper_threshold": parse_number(self.taper_threshold.get_text()),
                "tax_bands": self.tax_bands.get_bands(),
                "ni_bands": self.ni_bands.get_bands(),
            }
        except ValueError:
            self.status.set_markup("<span foreground='#c01c28'>All amounts and rates must be numbers</span>")
            return
        if not settings["tax_bands"]:
            self.status.set_markup("<span foreground='#c01c28'>Add at least one income tax band</span>")
            return
        try:
            taxcalc.save_settings(settings)
        except OSError as e:
            self.status.set_markup(f"<span foreground='#c01c28'>Could not save: {e}</span>")
            return
        self.app_window.settings = settings
        self.load(settings)
        self.status.set_text("Saved")
        self.app_window.estimate.refresh()


class AppWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Tax Estimator")
        self.set_default_size(720, 620)
        self.set_icon_name("accessories-calculator")
        self.settings = taxcalc.load_settings()

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.estimate = EstimatePage(self)
        self.settings_page = SettingsPage(self)
        stack.add_titled(self.estimate, "estimate", "Estimate")
        stack.add_titled(self.settings_page, "settings", "Settings")

        header = Gtk.HeaderBar(show_close_button=True)
        switcher = Gtk.StackSwitcher(stack=stack)
        header.set_custom_title(switcher)
        self.set_titlebar(header)
        self.add(stack)

        self.settings_page.load(self.settings)
        self.estimate.refresh()


def show_first_run_notice(parent):
    marker = taxcalc.CONFIG_DIR / "disclaimer-shown"
    if marker.exists():
        return
    dialog = Gtk.MessageDialog(
        transient_for=parent, modal=True, message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK, text="Estimates only",
    )
    dialog.format_secondary_markup(
        DISCLAIMER + f"\n\nThe built-in rates are for {taxcalc.DEFAULT_SETTINGS['tax_year']}. "
        "Update them under Settings for later tax years."
    )
    dialog.run()
    dialog.destroy()
    try:
        taxcalc.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass


def main():
    GLib.set_prgname("tax-estimator")
    GLib.set_application_name("Tax Estimator")
    win = AppWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.estimate.entry.grab_focus()
    show_first_run_notice(win)
    Gtk.main()


if __name__ == "__main__":
    main()
