import csv
import os
import sys
import tkinter as tk
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import messagebox, ttk


SALES_FILE = Path(__file__).resolve().parent / "sales.csv"
REGIONAL_FILE = Path(__file__).resolve().parent / "regional_sales.csv"
REQUIRED_COLUMNS = {
    "Date",
    "Order_ID",
    "Region",
    "Salesperson",
    "Product",
    "Category",
    "Quantity",
    "Unit_Price",
}
PRODUCT_NAMES = {
    "laptop stand": "Laptop Stand",
    "wireless mouse": "Wireless Mouse",
    "usb-c dock": "USB-C Dock",
    "webcam": "Webcam",
    "headset": "Headset",
}
NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}
TABLE_COLUMNS = (
    "Date",
    "Order_ID",
    "Region",
    "Salesperson",
    "Product",
    "Category",
    "Quantity",
    "Unit_Price",
    "Revenue",
)


def load_sales_data(file_path: Path = SALES_FILE) -> list[dict[str, str]]:
    """Load sales records from a CSV file and check its required headers."""
    with file_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("The sales CSV is empty or has no header row.")

        missing_columns = REQUIRED_COLUMNS.difference(
            name.strip() for name in reader.fieldnames
        )
        if missing_columns:
            raise ValueError(
                "The sales CSV is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )
        return list(reader)


def parse_quantity(value: str) -> int | None:
    value = NUMBER_WORDS.get(value.strip().lower(), value.strip())
    try:
        quantity = Decimal(value)
    except InvalidOperation:
        return None
    if quantity < 0 or quantity != quantity.to_integral_value():
        return None
    return int(quantity)


def parse_price(value: str) -> Decimal | None:
    try:
        price = Decimal(value.strip().replace("£", "").replace(",", ""))
    except InvalidOperation:
        return None
    return price if price >= 0 else None


def clean_sales_data(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Remove incomplete or unusable records and normalize display values."""
    cleaned_rows = []
    for row in rows:
        cleaned_row = {
            key.strip(): value.strip() if value is not None else ""
            for key, value in row.items()
            if key is not None
        }
        if any(not cleaned_row.get(column) for column in REQUIRED_COLUMNS):
            continue

        quantity = parse_quantity(cleaned_row["Quantity"])
        unit_price = parse_price(cleaned_row["Unit_Price"])
        if quantity is None or unit_price is None:
            continue

        product = cleaned_row["Product"]
        cleaned_row["Region"] = cleaned_row["Region"].title()
        cleaned_row["Salesperson"] = cleaned_row["Salesperson"].title()
        cleaned_row["Product"] = PRODUCT_NAMES.get(product.lower(), product.title())
        cleaned_row["Category"] = cleaned_row["Category"].title()
        cleaned_row["Quantity"] = str(quantity)
        cleaned_row["Unit_Price"] = f"{unit_price:.2f}"
        cleaned_row["Revenue"] = f"{quantity * unit_price:.2f}"
        cleaned_rows.append(cleaned_row)

    return cleaned_rows


def summarize_sales_by_region(
    rows: list[dict[str, str]],
) -> dict[str, Decimal]:
    """Calculate revenue totals by region."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        totals[row["Region"]] += Decimal(row["Revenue"])
    return dict(sorted(totals.items()))


def save_regional_summary(totals: dict[str, Decimal]) -> None:
    """Keep the regional summary CSV in sync with the cleaned sales data."""
    with REGIONAL_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Region", "Revenue"])
        for region, total in totals.items():
            writer.writerow([region, f"{total:.2f}"])


def configure_tcl_tk() -> None:
    """Correct stale Tcl/Tk paths using the active Python installation."""
    version = f"{tk.TclVersion:.1f}"
    installations = (Path(sys.prefix), Path(sys.base_prefix))

    for variable, folder in (
        ("TCL_LIBRARY", f"tcl{version}"),
        ("TK_LIBRARY", f"tk{version}"),
    ):
        configured_path = os.environ.get(variable)
        if configured_path and Path(configured_path).is_dir():
            continue

        for installation in installations:
            library_path = installation / "tcl" / folder
            if library_path.is_dir():
                os.environ[variable] = str(library_path)
                break


def sort_sales_rows(
    rows: list[dict[str, str]], column: str, descending: bool = False
) -> list[dict[str, str]]:
    """Return sales rows sorted numerically or alphabetically by a column."""
    if column in {"Quantity", "Unit_Price", "Revenue"}:
        key = lambda row: Decimal(row[column])
    else:
        key = lambda row: row[column].casefold()
    return sorted(rows, key=key, reverse=descending)


class SalesExplorer:
    def __init__(self, root: tk.Tk, rows: list[dict[str, str]]) -> None:
        self.root = root
        self.rows = rows
        self.product_filter = tk.StringVar(value="All products")
        self.region_filter = tk.StringVar(value="All regions")
        self.status = tk.StringVar()
        self.sort_column: str | None = None
        self.sort_descending = False

        self.root.title("Regional Product Sales")
        self.root.geometry("1120x650")
        self.root.minsize(800, 450)
        self.build_widgets()
        self.refresh_table()

    def build_widgets(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        ttk.Label(
            container, text="Regional Product Sales", font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        filters = ttk.Frame(container)
        filters.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        products = sorted({row["Product"] for row in self.rows})
        regions = sorted({row["Region"] for row in self.rows})
        ttk.Label(filters, text="Product").pack(side="left", padx=(0, 6))
        product_box = ttk.Combobox(
            filters,
            textvariable=self.product_filter,
            values=["All products", *products],
            state="readonly",
            width=22,
        )
        product_box.pack(side="left", padx=(0, 18))
        product_box.bind("<<ComboboxSelected>>", self.on_filter_changed)

        ttk.Label(filters, text="Region").pack(side="left", padx=(0, 6))
        region_box = ttk.Combobox(
            filters,
            textvariable=self.region_filter,
            values=["All regions", *regions],
            state="readonly",
            width=18,
        )
        region_box.pack(side="left", padx=(0, 18))
        region_box.bind("<<ComboboxSelected>>", self.on_filter_changed)

        ttk.Button(filters, text="Clear filters", command=self.clear_filters).pack(
            side="left"
        )

        ttk.Label(
            container, textvariable=self.status, font=("Segoe UI", 10, "bold")
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))

        table_frame = ttk.Frame(container)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.table = ttk.Treeview(
            table_frame, columns=TABLE_COLUMNS, show="headings", selectmode="browse"
        )
        for column in TABLE_COLUMNS:
            self.table.heading(
                column,
                text=column.replace("_", " "),
                command=lambda selected=column: self.sort_by_column(selected),
            )
            self.table.column(column, width=110, minwidth=75, anchor="w")
        self.table.column("Date", width=105)
        self.table.column("Order_ID", width=100)
        self.table.column("Region", width=100)
        self.table.column("Product", width=145)
        self.table.column("Quantity", width=80, anchor="center")
        self.table.column("Unit_Price", width=100, anchor="e")
        self.table.column("Revenue", width=100, anchor="e")

        vertical_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        horizontal_scroll = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.table.xview
        )
        self.table.configure(
            yscrollcommand=vertical_scroll.set,
            xscrollcommand=horizontal_scroll.set,
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")

    def on_filter_changed(self, _event: tk.Event) -> None:
        self.refresh_table()

    def clear_filters(self) -> None:
        self.product_filter.set("All products")
        self.region_filter.set("All regions")
        self.refresh_table()

    def sort_by_column(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = column
            self.sort_descending = False

        for heading in TABLE_COLUMNS:
            label = heading.replace("_", " ")
            if heading == self.sort_column:
                label += " ▼" if self.sort_descending else " ▲"
            self.table.heading(heading, text=label)
        self.refresh_table()

    def refresh_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)

        filtered_rows = [
            row
            for row in self.rows
            if self.product_filter.get() in ("All products", row["Product"])
            and self.region_filter.get() in ("All regions", row["Region"])
        ]
        if self.sort_column is not None:
            filtered_rows = sort_sales_rows(
                filtered_rows, self.sort_column, self.sort_descending
            )

        for row in filtered_rows:
            self.table.insert(
                "",
                "end",
                values=tuple(row[column] for column in TABLE_COLUMNS),
            )

        total = sum(
            (Decimal(row["Revenue"]) for row in filtered_rows), Decimal("0")
        )
        self.status.set(
            f"Showing {len(filtered_rows)} of {len(self.rows)} sales rows"
            f"    |    Total sales: GBP {total:.2f}"
        )


def main() -> None:
    configure_tcl_tk()
    try:
        sales_rows = clean_sales_data(load_sales_data())
        save_regional_summary(summarize_sales_by_region(sales_rows))
    except (OSError, csv.Error, ValueError) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Unable to load sales data", str(error))
        root.destroy()
        return

    root = tk.Tk()
    SalesExplorer(root, sales_rows)
    root.mainloop()


if __name__ == "__main__":
    main()
