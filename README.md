# QA_App_06

## `main.py`

`main.py` opens a desktop sales explorer for `sales.csv`. Use the
Product and Region dropdowns to filter the table; the displayed row count and
total sales update as filters change. Click **Clear filters** to show all rows.
Click any table column heading to sort by that column; click it again to reverse
the sort direction.
Rows with missing or unusable values are excluded. Regional sales are
calculated as `Quantity * Unit_Price`.

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