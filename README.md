# Tax Estimator

A small Linux desktop app that estimates the UK income tax and Class 4 National Insurance due on self-employed profits. Type in your taxable earnings (profit) and it shows the total bill, a band-by-band breakdown, your effective rate and your take-home.

> [!WARNING]
> **Estimates only. This is not tax or financial advice.**
> Tax bands and rates change, usually every April. Before relying on any figure, check that the bands in the app's Settings match the current figures on gov.uk:
> - [Income tax rates and allowances](https://www.gov.uk/income-tax-rates)
> - [Self-employed National Insurance rates](https://www.gov.uk/self-employed-national-insurance-rates)
>
> The software is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)). The author accepts no liability for decisions made using its output.

## What it covers

- Income tax at the basic, higher and additional rates (England, Wales and Northern Ireland)
- The personal allowance, including the taper of £1 for every £2 of income over £100,000
- Class 4 National Insurance at the main and upper rates

The built-in rates are for **2025/26**:

| | From profit of | Rate |
|---|---|---|
| Personal allowance | £0 | 0% |
| Basic rate | £12,570 | 20% |
| Higher rate | £50,270 | 40% |
| Additional rate | £125,140 | 45% |
| Class 4 NI main rate | £12,570 | 6% |
| Class 4 NI upper rate | £50,270 | 2% |

## What it doesn't cover

Scottish income tax rates, Class 2 NI, student loan repayments, pension contributions, Gift Aid, the marriage allowance, payments on account, other income (such as employment, dividends, savings or property), and any other reliefs or allowances.

## Requirements

- Linux with a graphical desktop (built on GNOME, should work on others)
- Python 3.8 or later
- GTK 3 Python bindings:
  - Debian/Ubuntu: `sudo apt install python3-gi gir1.2-gtk-3.0`
  - Fedora: `sudo dnf install python3-gobject gtk3`
  - Arch: `sudo pacman -S python-gobject gtk3`

## Install

1. Download the latest release (or clone this repo) and put the folder somewhere permanent. The app runs from that folder.
2. From inside the folder, run:
   ```sh
   ./install.sh
   ```
3. Open **Tax Estimator** from your app launcher.

You can also run it without installing: `python3 tax_estimator.py`.

If you move the folder later, run `./install.sh` again from the new location.

To remove the launcher, run `./uninstall.sh`. Add `--purge` to delete your saved settings too.

## Updating the rates

Open **Settings** to change the tax year label, the personal allowance, the taper threshold, and the income tax and NI bands. Enter each band's starting point as the profit figure published on gov.uk (for example, higher rate from £50,270). Double-click a cell to edit it. Press **Save** to keep your changes, or **Restore defaults** to go back to the built-in rates.

Settings are saved to `~/.config/tax-estimator/settings.json`. Copy that file to move your settings to another machine.

### How the income tax bands are applied

HMRC defines the higher and additional rate thresholds on *taxable income*, after the personal allowance has been deducted. The app converts each gov.uk-style profit threshold by subtracting the allowance that someone with exactly that profit would have. With a full allowance, £50,270 becomes £37,700 of taxable income. At £125,140 the allowance has fully tapered away, so that threshold stays at £125,140. This keeps the figures correct when the allowance is tapered above £100,000.

## Licence

[MIT](LICENSE) © 2026 Edd Savage
