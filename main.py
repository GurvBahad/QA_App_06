import csv
import json
import os
import sys
import tkinter as tk
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "app_config.json"
SalesRow = dict[str, str]
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
NUMERIC_COLUMNS = {"Quantity", "Unit_Price", "Revenue"}
CONFIG_PATH_KEYS = ("sales_file", "regional_file", "invoice_file")
WINDOW_SIZE_KEYS = (
    "window_width",
    "window_height",
    "min_window_width",
    "min_window_height",
)
TABLE_COLUMN_OPTIONS = {
    "Date": {"width": 105},
    "Order_ID": {"width": 100},
    "Region": {"width": 100},
    "Product": {"width": 145},
    "Quantity": {"width": 80, "anchor": "center"},
    "Unit_Price": {"width": 100, "anchor": "e"},
    "Revenue": {"width": 100, "anchor": "e"},
}


@dataclass(frozen=True)
class AppConfig:
    sales_file: Path
    regional_file: Path
    invoice_file: Path
    app_title: str
    window_width: int
    window_height: int
    min_window_width: int
    min_window_height: int
    currency_code: str


DEFAULT_CONFIG = {
    "sales_file": "sales.csv",
    "regional_file": "regional_sales.csv",
    "invoice_file": "sales_invoice.pdf",
    "app_title": "Regional Product Sales",
    "window_width": 1120,
    "window_height": 650,
    "min_window_width": 800,
    "min_window_height": 450,
    "currency_code": "GBP",
}


def load_app_config(file_path: Path = CONFIG_FILE) -> AppConfig:
    """Load and validate settings, using built-in defaults if no file exists."""
    try:
        settings = (
            json.loads(file_path.read_text(encoding="utf-8"))
            if file_path.exists()
            else {}
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {file_path.name}: {error.msg}") from error

    if not isinstance(settings, dict):
        raise ValueError(f"{file_path.name} must contain a JSON object.")

    unknown_keys = settings.keys() - DEFAULT_CONFIG.keys()
    if unknown_keys:
        raise ValueError(
            "Unknown setting(s) in "
            f"{file_path.name}: {', '.join(sorted(unknown_keys))}"
        )
    values = {**DEFAULT_CONFIG, **settings}

    paths = {}
    for key in CONFIG_PATH_KEYS:
        value = values[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} in {file_path.name} must be a non-empty path.")
        paths[key] = resolve_config_path(value)

    for key in ("app_title", "currency_code"):
        if not isinstance(values[key], str) or not values[key].strip():
            raise ValueError(f"{key} in {file_path.name} must be a non-empty string.")

    for key in WINDOW_SIZE_KEYS:
        if type(values[key]) is not int or values[key] <= 0:
            raise ValueError(f"{key} in {file_path.name} must be a positive integer.")

    if values["min_window_width"] > values["window_width"]:
        raise ValueError("min_window_width cannot exceed window_width.")
    if values["min_window_height"] > values["window_height"]:
        raise ValueError("min_window_height cannot exceed window_height.")

    return AppConfig(
        sales_file=paths["sales_file"],
        regional_file=paths["regional_file"],
        invoice_file=paths["invoice_file"],
        app_title=values["app_title"].strip(),
        window_width=values["window_width"],
        window_height=values["window_height"],
        min_window_width=values["min_window_width"],
        min_window_height=values["min_window_height"],
        currency_code=values["currency_code"].strip().upper(),
    )


def resolve_config_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def load_sales_data(file_path: Path) -> list[SalesRow]:
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
    if (
        not quantity.is_finite()
        or quantity < 0
        or quantity != quantity.to_integral_value()
    ):
        return None
    return int(quantity)


def parse_price(value: str) -> Decimal | None:
    try:
        price = Decimal(value.strip().replace("£", "").replace(",", ""))
    except InvalidOperation:
        return None
    return price if price.is_finite() and price >= 0 else None


def clean_sales_data(rows: list[SalesRow]) -> list[SalesRow]:
    """Remove incomplete or unusable records and normalize display values."""
    cleaned_rows: list[SalesRow] = []
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
    rows: list[SalesRow],
) -> dict[str, Decimal]:
    """Calculate revenue totals by region."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        totals[row["Region"]] += Decimal(row["Revenue"])
    return dict(sorted(totals.items()))


def save_regional_summary(totals: dict[str, Decimal], file_path: Path) -> None:
    """Keep the regional summary CSV in sync with the cleaned sales data."""
    with file_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Region", "Revenue"])
        for region, total in totals.items():
            writer.writerow([region, f"{total:.2f}"])


def pdf_text(x: int, y: int, text: str, size: int = 9) -> str:
    safe_text = text.encode("ascii", "replace").decode("ascii")
    escaped_text = safe_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return (
        f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm "
        f"({escaped_text}) Tj ET\n"
    )


def build_invoice_pages(rows: list[SalesRow], currency_code: str) -> list[bytes]:
    if not rows:
        raise ValueError("There are no valid sales rows to include in the invoice.")

    pages: list[str] = []
    commands = ""
    page_number = 0
    y = 0

    def start_page() -> None:
        nonlocal commands, page_number, y
        page_number += 1
        title = "Sales Invoice Summary" if page_number == 1 else "Sales Invoice Summary (continued)"
        commands = pdf_text(42, 752, title, 18)
        if page_number == 1:
            commands += pdf_text(42, 729, f"Invoice date: {date.today().isoformat()}")
            commands += pdf_text(42, 713, f"Currency: {currency_code}")
        else:
            commands += pdf_text(42, 729, f"Invoice date: {date.today().isoformat()}")
        commands += "0.7 w 42 697 m 570 697 l S\n"
        commands += pdf_text(42, 681, "Date")
        commands += pdf_text(98, 681, "Order")
        commands += pdf_text(151, 681, "Region")
        commands += pdf_text(220, 681, "Product")
        commands += pdf_text(383, 681, "Qty")
        commands += pdf_text(424, 681, "Unit price")
        commands += pdf_text(506, 681, "Line total")
        commands += "0.5 w 42 674 m 570 674 l S\n"
        y = 655

    def finish_page() -> None:
        nonlocal commands
        commands += f"BT /F1 8 Tf 1 0 0 1 520 25 Tm (Page {page_number}) Tj ET\n"
        pages.append(commands.encode("ascii"))

    start_page()
    grand_total = Decimal("0")
    for row in rows:
        if y < 55:
            finish_page()
            start_page()

        quantity = int(row["Quantity"])
        unit_price = Decimal(row["Unit_Price"])
        line_total = Decimal(row["Revenue"])
        grand_total += line_total
        product = row["Product"]
        if len(product) > 25:
            product = product[:22] + "..."
        values = (
            (42, row["Date"]),
            (98, row["Order_ID"]),
            (151, row["Region"]),
            (220, product),
            (383, str(quantity)),
            (424, f"{unit_price:.2f}"),
            (506, f"{line_total:.2f}"),
        )
        for x, value in values:
            commands += pdf_text(x, y, value, 8)
        y -= 18

    if y < 78:
        finish_page()
        start_page()
    total_line_y = y - 8
    total_text_y = y - 26
    commands += f"0.7 w 390 {total_line_y} m 570 {total_line_y} l S\n"
    commands += pdf_text(390, total_text_y, f"Grand total ({currency_code})", 10)
    commands += pdf_text(506, total_text_y, f"{grand_total:.2f}", 10)
    finish_page()
    return pages


def save_invoice_pdf(
    rows: list[SalesRow], file_path: Path, currency_code: str
) -> None:
    """Write all valid sales as line items in a simple multi-page PDF."""
    page_streams = build_invoice_pages(rows, currency_code)
    objects: list[bytes | None] = [None] * (4 + 2 * len(page_streams))
    page_ids = [4 + index * 2 for index in range(len(page_streams))]

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for page_id, stream in zip(page_ids, page_streams):
        stream_id = page_id + 1
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>"
        ).encode("ascii")
        objects[stream_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, len(objects)):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id] or b"")
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    file_path.write_bytes(pdf)


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
    rows: list[SalesRow], column: str, descending: bool = False
) -> list[SalesRow]:
    """Return sales rows sorted numerically or alphabetically by a column."""
    if column in NUMERIC_COLUMNS:
        key = lambda row: Decimal(row[column])
    else:
        key = lambda row: row[column].casefold()
    return sorted(rows, key=key, reverse=descending)


class SalesExplorer:
    def __init__(
        self, root: tk.Tk, rows: list[SalesRow], config: AppConfig
    ) -> None:
        self.root = root
        self.rows = rows
        self.config = config
        self.product_filter = tk.StringVar(value="All products")
        self.region_filter = tk.StringVar(value="All regions")
        self.status = tk.StringVar()
        self.sort_column: str | None = None
        self.sort_descending = False

        self.root.title(config.app_title)
        self.root.geometry(f"{config.window_width}x{config.window_height}")
        self.root.minsize(config.min_window_width, config.min_window_height)
        self.build_widgets()
        self.refresh_table()

    def build_widgets(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        ttk.Label(
            container, text=self.config.app_title, font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        self._build_filter_controls(container)
        ttk.Label(
            container, textvariable=self.status, font=("Segoe UI", 10, "bold")
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))
        self._build_sales_table(container)

    def _build_filter_controls(self, container: ttk.Frame) -> None:
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
        ttk.Button(
            filters, text="Export invoice PDF", command=self.export_invoice
        ).pack(side="left", padx=(12, 0))

    def _build_sales_table(self, container: ttk.Frame) -> None:
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
            options = {"width": 110, "minwidth": 75, "anchor": "w"}
            options.update(TABLE_COLUMN_OPTIONS.get(column, {}))
            self.table.column(column, **options)

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

    def export_invoice(self) -> None:
        initial_dir = (
            self.config.invoice_file.parent
            if self.config.invoice_file.parent.is_dir()
            else BASE_DIR
        )
        file_name = filedialog.asksaveasfilename(
            title="Save sales invoice",
            initialdir=initial_dir,
            initialfile=self.config.invoice_file.name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not file_name:
            return
        try:
            save_invoice_pdf(
                self.rows, Path(file_name), self.config.currency_code
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("Unable to create invoice", str(error), parent=self.root)
            return
        messagebox.showinfo(
            "Invoice created",
            f"Sales invoice saved to:\n{file_name}",
            parent=self.root,
        )

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

    def _filtered_rows(self) -> list[SalesRow]:
        rows = [
            row
            for row in self.rows
            if self.product_filter.get() in ("All products", row["Product"])
            and self.region_filter.get() in ("All regions", row["Region"])
        ]
        if self.sort_column is not None:
            return sort_sales_rows(rows, self.sort_column, self.sort_descending)
        return rows

    def refresh_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)

        filtered_rows = self._filtered_rows()
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
            f"    |    Total sales: {self.config.currency_code} {total:.2f}"
        )


def main() -> None:
    configure_tcl_tk()
    try:
        config = load_app_config()
        sales_rows = clean_sales_data(load_sales_data(config.sales_file))
        save_regional_summary(
            summarize_sales_by_region(sales_rows), config.regional_file
        )
    except (OSError, csv.Error, ValueError) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Unable to start sales app", str(error))
        root.destroy()
        return

    root = tk.Tk()
    SalesExplorer(root, sales_rows, config)
    root.mainloop()


if __name__ == "__main__":
    main()
