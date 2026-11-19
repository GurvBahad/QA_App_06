# QA_App_06

## `main.py`

`main.py` opens a desktop sales explorer for `sales.csv`. Use the
Product and Region dropdowns to filter the table; the displayed row count and
total sales update as filters change. Click **Clear filters** to show all rows.
Click any table column heading to sort by that column; click it again to reverse
the sort direction.
Rows with missing or unusable values are excluded. Regional sales are
calculated as `Quantity * Unit_Price`.

Use **Export invoice PDF** to save a combined sales invoice summary containing
all valid sales rows and a grand total. The app suggests `sales_invoice.pdf`
in the project folder. This is a sales summary, not a tax invoice, because the
CSV does not include customer, seller, or tax details.

The app uses separate functions to load, clean, and summarize the data:

- `load_sales_data()` reads the CSV records.
- `clean_sales_data()` removes incomplete rows and standardizes display values.
- `summarize_sales_by_region()` calculates regional revenue totals.

The app also refreshes `regional_sales.csv` when it starts. Run the app from
the repository root:

```bash
python main.py
```

Tkinter is included with most standard Python installations.
If startup reports that Tcl/Tk is missing, choose a Python installation that
includes Tcl/Tk as the project interpreter in your IDE. The app corrects stale
`TCL_LIBRARY` and `TK_LIBRARY` paths when the active Python installation has
the Tcl/Tk files available.

## Configuration

Edit `app_config.json` to change the sales CSV path, regional summary output,
default invoice filename, window title and size, or displayed currency code.
Relative file paths are resolved from the project folder; absolute paths are
also supported. If the config file is missing, the app uses built-in defaults.