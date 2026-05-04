#1 chương trình simple store management
# (Chương trình quản lý của hàng đơn giản: load dữ liệu là file csv,
#  tìm kiếm và thêm danh mục vào giỏ hàng. tiến hành thanh toán và
# in tổng tiền)

# Import thư viện
import sys
import pandas as pd
from datetime import datetime
# Import toàn bộ widget cần dùng trong PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton,
    QTextEdit, QLabel,
    QAction, QFileDialog,
    QMessageBox, QSpinBox,
    QDialog, QHeaderView,
    QFrame, QStatusBar,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


# =========================================================
#  POPUP HÓA ĐƠN (Checkout Dialog)
# =========================================================
class CheckoutDialog(QDialog):
    def __init__(self, cart: list, parent=None):
        super().__init__(parent)  # gọi constructor của QDialog
        self.setWindowTitle("Bill Information")  # tiêu đề cửa sổ
        self.setMinimumWidth(850)  # chiều rộng tối thiểu
        self.cart = cart  # lưu giỏ hàng
        self._build_ui()  # tạo giao diện

    def _build_ui(self):
        # layout chính theo chiều dọc
        layout = QVBoxLayout(self)

        # ================= TITLE =================
        title = QLabel(" Receipt")  # tiêu đề hóa đơn
        title.setFont(QFont("Arial", 14, QFont.Bold))  # font chữ
        title.setAlignment(Qt.AlignCenter)  # căn giữa
        layout.addWidget(title)

        # ================= DATE =================
        dt_label = QLabel(
            f"Date: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}"
        )  # thời gian hiện tại
        dt_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(dt_label)

        # ================= SEPARATOR =================
        layout.addWidget(self._separator())

        # ================= BILL TEXT =================
        self.bill_area = QTextEdit()  # vùng hiển thị hóa đơn
        self.bill_area.setReadOnly(True)  # không cho sửa
        self.bill_area.setStyleSheet("""
            QTextEdit {
                font-family: Consolas;
                font-size: 18px;
                line-height: 1.6;
                padding: 10px;
                background-color: #ffffff;
                border: none;
            }
        """)  # font monospace
        layout.addWidget(self.bill_area)

        layout.addWidget(self._separator())

        # ================= TOTAL =================
        total = sum(row["subtotal"] for row in self.cart)  # tính tổng tiền
        self.total_label = QLabel(f"TOTAL:  ${total:,.2f}")
        self.total_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.total_label)

        # ================= BUTTON =================
        btn_row = QHBoxLayout()

        back_btn = QPushButton("◀  Back")  # quay lại
        back_btn.clicked.connect(self.reject)

        close_btn = QPushButton("✔  Close")  # đóng
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

        # đổ dữ liệu vào hóa đơn
        self._populate_bill()

    def _separator(self):
        # tạo đường kẻ ngang
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        return line

    def _populate_bill(self):
        lines = []

        # header bảng
        lines.append(f"{'Customer ID':<15} | {'Product':<28} | {'Qty':>4} | {'Unit':>8} | {'Sub':>10} |")
        lines.append("-" * 77)

        # duyệt từng item trong cart
        for row in self.cart:
            lines.append(
                f"{row['customer_id']:<15} | {row['name']:<28} | {row['qty']:>4} | "
                f"{row['price']:>7,.2f}$ | {row['subtotal']:>9,.2f}$ |"
            )

        # hiển thị vào text box
        self.bill_area.setPlainText("\n".join(lines))


# =========================================================
#  MAIN WINDOW
# =========================================================
class StoreMainWindow(QMainWindow):

    # các cột cần hiển thị từ CSV
    DISPLAY_COLS = [
        "Transaction ID",
        "Date",
        "Customer ID",
        "Gender",
        "Age",
        "Product Category",
        "Quantity",
        "Price per Unit",
        "Total Amount"
    ]

    def __init__(self):
        super().__init__()

        # DataFrame gốc (toàn bộ dữ liệu CSV)
        self.df = None

        # DataFrame sau khi filter (search)
        self.filtered_df = None

        # giỏ hàng (list các dict)
        self.cart = []


        self.setWindowTitle("Simple Store Management")
        self.setMinimumSize(900, 600)

        self._build_menu()  # tạo menu
        self._build_ui()    # tạo giao diện
        self._build_status_bar()  # thanh trạng thái

        self._apply_theme()

    # =====================================================
    # MENU
    # =====================================================
    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        # action mở file
        open_action = QAction("Open CSV…", self)
        open_action.triggered.connect(self._open_file)

        # action thoát
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)

        # ================= LEFT PANEL =================
        left = QVBoxLayout()

        # ---------- SEARCH ----------
        search_row = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.textChanged.connect(self._on_search)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_search)

        search_row.addWidget(QLabel("Search:"))
        search_row.addWidget(self.search_box)
        search_row.addWidget(clear_btn)

        left.addLayout(search_row)

        # ---------- TABLE ----------
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.DISPLAY_COLS))
        self.table.setHorizontalHeaderLabels(self.DISPLAY_COLS)

        self.table.setAlternatingRowColors(True)

        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007acc, stop:1 #4dd2ff
                );
                color: black;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #ccc;
            }
        """)

        # Auto resize dòng
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # chọn theo dòng
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # không cho edit
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # stretch cột
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)

        # khi chọn dòng → show detail
        self.table.selectionModel().selectionChanged.connect(
            self._on_row_selected
        )

        left.addWidget(self.table)

        # ---------- DETAIL ----------
        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setStyleSheet("""
            QTextEdit {
                font-family: Segoe UI;
                font-size: 22px;
                padding: 10px;
                line-height: 1.6;
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)
        left.addWidget(self.detail_area)

        # ---------- ADD TO CART ----------
        add_row = QHBoxLayout()

        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)

        add_btn = QPushButton("Add to Cart")
        add_btn.setStyleSheet("background-color: #0078D7; color: white")
        add_btn.clicked.connect(self._add_to_cart)

        add_row.addWidget(self.qty_spin)
        add_row.addWidget(add_btn)

        left.addLayout(add_row)

        # ================= RIGHT PANEL =================
        right = QVBoxLayout()

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)

        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.cart_table.setHorizontalHeaderLabels(
            ["Transaction ID", "Customer ID", "Product category", "Qty", "Unit Price", "Subtotal"]
        )

        right.addWidget(self.cart_table)
        self.cart_table.setStyleSheet("""
            QHeaderView::section {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007acc, stop:1 #4dd2ff
                );
                color: black;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #ccc;
            }
        """)

        # tổng tiền
        self.cart_total_label = QLabel("Total: $0.00")
        right.addWidget(self.cart_total_label)

        # nút remove
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("background-color: #dc3545; color: white")
        remove_btn.clicked.connect(self._remove_from_cart)

        # nút checkout
        checkout_btn = QPushButton("Checkout")
        checkout_btn.setStyleSheet("background-color: #28a745; color: white")
        checkout_btn.clicked.connect(self._checkout)

        right.addWidget(remove_btn)
        right.addWidget(checkout_btn)

        root.addLayout(left, 3)
        root.addLayout(right, 2)

        root.setSpacing(10)
        left.setSpacing(10)
        right.setSpacing(10)

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)


    # =====================================================
    # LOAD CSV (PANDAS)
    # =====================================================
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self)

        if not path:
            return

        # đọc CSV → DataFrame
        self.df = pd.read_csv(path)

        # copy sang filtered_df
        self.filtered_df = self.df.copy()

        # hiển thị lên table
        self._populate_table(self.filtered_df)


    # =====================================================
    # HIỂN THỊ TABLE
    # =====================================================
    def _populate_table(self, df):
        self.table.setRowCount(0)

        # duyệt từng dòng DataFrame
        for _, row in df.iterrows():
            r = self.table.rowCount()
            self.table.insertRow(r)

            for c, col in enumerate(self.DISPLAY_COLS):
                val = str(row[col])  # lấy dữ liệu theo tên cột
                self.table.setItem(r, c, QTableWidgetItem(val))


    # =====================================================
    # SEARCH (LOGIC PANDAS)
    # =====================================================
    def _on_search(self, text):
        if self.df is None:
            return

        if not text:
            self.filtered_df = self.df.copy()
        else:
            # apply từng cột → tìm keyword
            mask = self.df.astype(str).apply(
                lambda col: col.str.contains(text, case=False, na=False)
            ).any(axis=1)

            self.filtered_df = self.df[mask]

        self._populate_table(self.filtered_df)

    def _clear_search(self):
        self.search_box.clear()

    # =====================================================
    # DETAIL
    # =====================================================
    def _on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        idx = rows[0].row()

        # lấy dòng từ DataFrame
        row = self.filtered_df.iloc[idx]

        # hiển thị tất cả cột
        # text = "\n".join(f"{col}: {row[col]}" for col in self.df.columns)
        # text = "\n".join(f"• {col}: {row[col]}" for col in self.df.columns)
        text = "\n".join(f"- {col}: {row[col]}" for col in self.df.columns)
        self.detail_area.setPlainText(text)


    # =====================================================
    # ADD TO CART
    # =====================================================
    def _add_to_cart(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        idx = rows[0].row()
        row = self.filtered_df.iloc[idx]

        qty = self.qty_spin.value()

        transaction_id = row["Transaction ID"]
        customer_id = row["Customer ID"]
        name = row["Product Category"]
        price = float(row["Price per Unit"])
        subtotal = price * qty

        # check trùng
        for item in self.cart:
            if item["transaction_id"] == row["Transaction ID"]:
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                self._refresh_cart_table()
                return

        # thêm mới
        self.cart.append({
            "transaction_id": transaction_id,
            "customer_id": customer_id,
            "name": name,
            "qty": qty,
            "price": price,
            "subtotal": subtotal
        })

        self._refresh_cart_table()

    # =====================================================
    # UPDATE CART UI
    # =====================================================
    def _refresh_cart_table(self):
        self.cart_table.setRowCount(0)

        total = 0

        for item in self.cart:
            r = self.cart_table.rowCount()
            self.cart_table.insertRow(r)


            self.cart_table.setItem(r, 0, QTableWidgetItem(str(item["transaction_id"])))
            self.cart_table.setItem(r, 1, QTableWidgetItem(str(item["customer_id"])))
            self.cart_table.setItem(r, 2, QTableWidgetItem(item["name"]))
            self.cart_table.setItem(r, 3, QTableWidgetItem(str(item["qty"])))
            self.cart_table.setItem(r, 4, QTableWidgetItem(str(item["price"])))
            self.cart_table.setItem(r, 5, QTableWidgetItem(str(item["subtotal"])))

            total += item["subtotal"]

        self.cart_total_label.setText(f"Total: ${total}")

    # =====================================================
    # REMOVE
    # =====================================================
    def _remove_from_cart(self):
        rows = self.cart_table.selectionModel().selectedRows()
        if not rows:
            return

        idx = rows[0].row()
        self.cart.pop(idx)

        self._refresh_cart_table()

    # =====================================================
    # CHECKOUT
    # =====================================================
    def _checkout(self):
        if not self.cart:
            return

        dlg = CheckoutDialog(self.cart, self)
        dlg.exec_()

        self.cart.clear()
        self._refresh_cart_table()

    def _apply_theme(self):
        self.setStyleSheet("""
            QWidget {
                font-family: Segoe UI;
                font-size: 13px;
                background-color: #f5f5f5;
            }

            QLineEdit {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background: white;
            }

            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #0078D7;
                color: white;
            }

            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #0078D7;
                color: white;
            }
                
                QPushButton:hover {
                background-color: #3399ff;
            }
                
                QPushButton:pressed {
                background-color: #005A9E;
            }

            QTableWidget {
                background-color: white;
                gridline-color: #ddd;
                selection-background-color: #cce6ff;
            }

            QHeaderView::section {
                background-color: #0078D7;
                color: white;
                padding: 6px;
                border: none;
            }
            
            QTableWidget::item:hover {
                background-color: #d0ebff;
                border: 1px solid #90caff;
            }
            
            QTableWidget::item:selected {
                background-color: #4da6ff;
                color: white;
                font-weight: bold;
            }
            
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
            }
            
            QScrollBar::handle:vertical {
                background: #b0c4de;
                border-radius: 4px;
            }
            
        """)


# =========================================================
# MAIN
# =========================================================
def main():
    app = QApplication(sys.argv)

    window = StoreMainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()