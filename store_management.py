import sys
import os
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QLabel,
    QAction,
    QFileDialog,
    QMessageBox,
    QSpinBox,
    QDialog,
    QHeaderView,
    QFrame,
    QStatusBar,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


# ─────────────────────────────────────────────
#  Checkout / Bill Dialog
# ─────────────────────────────────────────────
class CheckoutDialog(QDialog):
    def __init__(self, cart: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bill Information")
        self.setMinimumWidth(480)
        self.cart = cart
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("🧾  Receipt")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Date / time
        dt_label = QLabel(f"Date: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
        dt_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(dt_label)

        layout.addWidget(self._separator())

        # Bill text area
        self.bill_area = QTextEdit()
        self.bill_area.setReadOnly(True)
        self.bill_area.setFont(QFont("Courier New", 10))
        layout.addWidget(self.bill_area)

        layout.addWidget(self._separator())

        # Total
        total = sum(row["subtotal"] for row in self.cart)
        self.total_label = QLabel(f"TOTAL:  ${total:,.2f}")
        self.total_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.total_label)

        # Buttons
        btn_row = QHBoxLayout()
        back_btn = QPushButton("◀  Back")
        back_btn.clicked.connect(self.reject)
        close_btn = QPushButton("✔  Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._populate_bill()

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _populate_bill(self):
        lines = []
        lines.append(f"{'Product':<28} {'Qty':>4}  {'Unit':>8}  {'Sub':>10}")
        lines.append("-" * 56)
        for row in self.cart:
            lines.append(
                f"{row['name']:<28} {row['qty']:>4}  "
                f"${row['price']:>7,.2f}  ${row['subtotal']:>9,.2f}"
            )
        self.bill_area.setPlainText("\n".join(lines))


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────
class StoreMainWindow(QMainWindow):
    # Columns we want to display from the CSV
    DISPLAY_COLS = ["Transaction ID", "Product Category", "Price per Unit", "Quantity"]

    def __init__(self):
        super().__init__()
        self.df: pd.DataFrame | None = None  # full dataset
        self.filtered_df: pd.DataFrame | None = None
        self.cart: list = []  # list of dicts

        self.setWindowTitle("Simple Store Management")
        self.setMinimumSize(900, 600)
        self._build_menu()
        self._build_ui()
        self._build_status_bar()

    # ── Menu bar ──────────────────────────────
    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open CSV…", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # ── Central widget ────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Left panel: book/product list ──
        left = QVBoxLayout()

        # Search row
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by product category or ID…")
        self.search_box.textChanged.connect(self._on_search)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear_search)
        search_row.addWidget(QLabel("Search:"))
        search_row.addWidget(self.search_box)
        search_row.addWidget(clear_btn)
        left.addLayout(search_row)

        # Product table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.DISPLAY_COLS))
        self.table.setHorizontalHeaderLabels(self.DISPLAY_COLS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._on_row_selected)
        left.addWidget(self.table)

        # Detail area
        left.addWidget(QLabel("Detail:"))
        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setFixedHeight(110)
        left.addWidget(self.detail_area)

        # Add-to-cart row
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Quantity:"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(999)
        self.qty_spin.setValue(1)
        add_row.addWidget(self.qty_spin)
        add_btn = QPushButton("➕  Add to Cart")
        add_btn.clicked.connect(self._add_to_cart)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        left.addLayout(add_row)

        root.addLayout(left, 3)

        # ── Right panel: cart ──
        right = QVBoxLayout()
        right.addWidget(QLabel("🛒  Cart:"))

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(4)
        self.cart_table.setHorizontalHeaderLabels(
            ["Product", "Qty", "Unit Price", "Subtotal"]
        )
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right.addWidget(self.cart_table)

        # Cart total label
        self.cart_total_label = QLabel("Total: $0.00")
        self.cart_total_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.cart_total_label.setAlignment(Qt.AlignRight)
        right.addWidget(self.cart_total_label)

        remove_btn = QPushButton("🗑  Remove Selected")
        remove_btn.clicked.connect(self._remove_from_cart)
        right.addWidget(remove_btn)

        checkout_btn = QPushButton("💳  Checkout")
        checkout_btn.setFixedHeight(40)
        checkout_btn.setFont(QFont("Arial", 11, QFont.Bold))
        checkout_btn.clicked.connect(self._checkout)
        right.addWidget(checkout_btn)

        root.addLayout(right, 2)

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Click File → Open CSV to load data.")

    # ── File loading ──────────────────────────
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV file", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            self.df = pd.read_csv(path)
            # Validate required columns
            missing = [c for c in self.DISPLAY_COLS if c not in self.df.columns]
            if missing:
                QMessageBox.warning(
                    self,
                    "Column mismatch",
                    f"Missing columns: {missing}\nLoaded anyway.",
                )
            self.filtered_df = self.df.copy()
            self._populate_table(self.filtered_df)
            self.status.showMessage(f"Loaded {len(self.df)} records from: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error loading file", str(exc))

    # ── Table population ──────────────────────
    def _populate_table(self, df: pd.DataFrame):
        self.table.setRowCount(0)
        for _, row in df.iterrows():
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, col in enumerate(self.DISPLAY_COLS):
                val = str(row[col]) if col in df.columns else ""
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

    # ── Search ────────────────────────────────
    def _on_search(self, text: str):
        if self.df is None:
            return
        if not text.strip():
            self.filtered_df = self.df.copy()
        else:
            mask = self.df.apply(
                lambda col: col.astype(str).str.contains(text, case=False, na=False)
            ).any(axis=1)
            self.filtered_df = self.df[mask].copy()
        self._populate_table(self.filtered_df)
        self.status.showMessage(f"{len(self.filtered_df)} result(s) found.")

    def _clear_search(self):
        self.search_box.clear()

    # ── Row selection → detail ────────────────
    def _on_row_selected(self):
        if self.filtered_df is None:
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.detail_area.clear()
            return
        idx = rows[0].row()
        row = self.filtered_df.iloc[idx]
        lines = [f"{col}: {row[col]}" for col in self.df.columns]
        self.detail_area.setPlainText("\n".join(lines))

    # ── Add to cart ───────────────────────────
    def _add_to_cart(self):
        if self.filtered_df is None:
            self.status.showMessage("Load a CSV file first.")
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self, "No selection", "Please select a product first."
            )
            return
        idx = rows[0].row()
        row = self.filtered_df.iloc[idx]
        qty = self.qty_spin.value()
        name = str(row.get("Product Category", "Unknown"))
        price = float(row.get("Price per Unit", 0))
        subtotal = price * qty

        # Check if already in cart → update qty
        for item in self.cart:
            if item["transaction_id"] == row.get("Transaction ID"):
                item["qty"] += qty
                item["subtotal"] = item["price"] * item["qty"]
                self._refresh_cart_table()
                return

        self.cart.append(
            {
                "transaction_id": row.get("Transaction ID"),
                "name": name,
                "qty": qty,
                "price": price,
                "subtotal": subtotal,
            }
        )
        self._refresh_cart_table()
        self.status.showMessage(f"Added {qty}× {name} to cart.")

    # ── Cart display ──────────────────────────
    def _refresh_cart_table(self):
        self.cart_table.setRowCount(0)
        total = 0.0
        for entry in self.cart:
            r = self.cart_table.rowCount()
            self.cart_table.insertRow(r)
            self.cart_table.setItem(r, 0, QTableWidgetItem(entry["name"]))
            self.cart_table.setItem(r, 1, QTableWidgetItem(str(entry["qty"])))
            self.cart_table.setItem(r, 2, QTableWidgetItem(f"${entry['price']:,.2f}"))
            self.cart_table.setItem(
                r, 3, QTableWidgetItem(f"${entry['subtotal']:,.2f}")
            )
            for c in range(4):
                if self.cart_table.item(r, c):
                    self.cart_table.item(r, c).setTextAlignment(Qt.AlignCenter)
            total += entry["subtotal"]
        self.cart_total_label.setText(f"Total: ${total:,.2f}")

    # ── Remove from cart ──────────────────────
    def _remove_from_cart(self):
        rows = self.cart_table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        removed = self.cart.pop(idx)
        self._refresh_cart_table()
        self.status.showMessage(f"Removed {removed['name']} from cart.")

    # ── Checkout ──────────────────────────────
    def _checkout(self):
        if not self.cart:
            QMessageBox.information(self, "Empty Cart", "Your cart is empty.")
            return
        dlg = CheckoutDialog(self.cart, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.cart.clear()
            self._refresh_cart_table()
            self.status.showMessage("Checkout complete. Cart cleared.")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
def main():
    # On Linux Wayland sessions, Qt can default to xcb and crash if xcb deps are missing.
    # Prefer wayland automatically when the user has not explicitly selected a platform.
    if (
        sys.platform.startswith("linux")
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        and "QT_QPA_PLATFORM" not in os.environ
    ):
        os.environ["QT_QPA_PLATFORM"] = "wayland"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = StoreMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
