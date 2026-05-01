from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, 
                             QComboBox, QFormLayout, QDateEdit, QTimeEdit, QSpinBox, 
                             QDoubleSpinBox, QGridLayout, QFrame, QCheckBox)
from PyQt6.QtCore import Qt, QDate, QTime, QTimer
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import datetime
from database import DatabaseManager

class BaseScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Tiêu đề màn hình
        self.lbl_title = QLabel("Screen Title")
        self.lbl_title.setObjectName("title")
        self.main_layout.addWidget(self.lbl_title)
        
        # Thông báo inline (Thành công / Lỗi)
        self.lbl_msg = QLabel("")
        self.lbl_msg.hide()
        self.main_layout.addWidget(self.lbl_msg)

    def show_message(self, msg, is_error=False):
        self.lbl_msg.setText(msg)
        color = "#e74c3c" if is_error else "#27ae60"
        self.lbl_msg.setStyleSheet(f"color: {color}; font-weight: bold; background-color: {'#fadbd8' if is_error else '#d5f5e3'}; padding: 8px; border-radius: 4px;")
        self.lbl_msg.show()
        # Tự ẩn sau 4 giây
        QTimer.singleShot(4000, self.lbl_msg.hide)

    def validate_inputs(self, inputs):
        """Kiểm tra input rỗng và đổi màu viền"""
        is_valid = True
        for widget in inputs:
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                widget.setStyleSheet("border: 1px solid red;")
                is_valid = False
            elif isinstance(widget, QComboBox) and widget.currentData() is None:
                widget.setStyleSheet("border: 1px solid red;")
                is_valid = False
            else:
                widget.setStyleSheet("") # Reset
        return is_valid

    def setup_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

# --- 1. Dashboard ---
class DashboardScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Tổng Quan (Dashboard)")
        
        # Thẻ thống kê
        stats_layout = QHBoxLayout()
        self.cards = {
            "customers": self.create_stat_card("Tổng khách hàng", "0", "#3498db"),
            "tables": self.create_stat_card("Bàn trống", "0", "#2ecc71"),
            "reservations": self.create_stat_card("Đặt chỗ hôm nay", "0", "#f1c40f"),
            "revenue": self.create_stat_card("Doanh thu tháng", "0 đ", "#e67e22")
        }
        for card in self.cards.values():
            stats_layout.addWidget(card)
        self.main_layout.addLayout(stats_layout)

        # Nút Refresh
        btn_refresh = QPushButton("Làm mới dữ liệu")
        btn_refresh.clicked.connect(self.load_data)
        self.main_layout.addWidget(btn_refresh, alignment=Qt.AlignmentFlag.AlignRight)

        # Bảng đặt chỗ hôm nay
        self.main_layout.addWidget(QLabel("<b>Danh sách đặt bàn hôm nay:</b>"))
        self.table = self.setup_table(["ID", "Khách hàng", "Bàn", "Thời gian", "Số khách", "Trạng thái"])
        self.main_layout.addWidget(self.table)

    def create_stat_card(self, title, value, color):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {color}; color: white; border-radius: 8px; padding: 15px;")
        layout = QVBoxLayout(frame)
        lbl_t = QLabel(title)
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet("font-size: 20pt; font-weight: bold;")
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return frame

    def load_data(self):
        try:
            # FIX: Thêm điều kiện lọc khách hủy bàn và hóa đơn chưa thanh toán
            cust_count = self.db.query("SELECT COUNT(*) as c FROM Customers")[0]['c']
            tbl_count = self.db.query("SELECT COUNT(*) as c FROM Tables WHERE Status='Available'")[0]['c']
            
            res_count = self.db.query("""
                SELECT COUNT(*) as c FROM Reservations 
                WHERE DATE(ReservationDate) = CURDATE() AND Status NOT IN ('Cancelled', 'NoShow')
            """)[0]['c']
            
            rev_sum = self.db.query("""
                SELECT SUM(TotalAmount) as s FROM Invoices 
                WHERE Status = 'Paid' 
                  AND MONTH(PaymentDate) = MONTH(CURDATE()) 
                  AND YEAR(PaymentDate) = YEAR(CURDATE())
            """)[0]['s']
            
            self.cards["customers"].findChildren(QLabel)[1].setText(str(cust_count))
            self.cards["tables"].findChildren(QLabel)[1].setText(str(tbl_count))
            self.cards["reservations"].findChildren(QLabel)[1].setText(str(res_count))
            self.cards["revenue"].findChildren(QLabel)[1].setText(f"{rev_sum or 0:,.0f} đ")

            # Load bảng (Giữ nguyên)
            res_data = self.db.query("""
                SELECT r.ReservationID, c.CustomerName, t.TableNumber, r.ReservationTime, r.GuestCount, r.Status
                FROM Reservations r
                JOIN Customers c ON r.CustomerID = c.CustomerID
                JOIN Tables t ON r.TableID = t.TableID
                WHERE DATE(r.ReservationDate) = CURDATE()
                ORDER BY r.ReservationTime ASC
            """)
            self.table.setRowCount(0)
            for row, item in enumerate(res_data):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item['ReservationID'])))
                self.table.setItem(row, 1, QTableWidgetItem(item['CustomerName']))
                self.table.setItem(row, 2, QTableWidgetItem(str(item['TableNumber'])))
                self.table.setItem(row, 3, QTableWidgetItem(str(item['ReservationTime'])))
                self.table.setItem(row, 4, QTableWidgetItem(str(item['GuestCount'])))
                self.table.setItem(row, 5, QTableWidgetItem(item['Status']))
        except Exception as e:
            self.show_message(str(e), True)

# --- 2. Quản lý khách hàng ---
class CustomerScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Quản lý Khách Hàng")
        self.current_id = None

        # Search
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Tìm kiếm theo tên hoặc SĐT (Realtime)...")
        self.txt_search.textChanged.connect(self.load_data)
        self.main_layout.addWidget(self.txt_search)

        # Bảng
        self.table = self.setup_table(["ID", "Tên khách hàng", "SĐT", "Email", "Địa chỉ"])
        self.table.itemSelectionChanged.connect(self.on_select)
        self.main_layout.addWidget(self.table)

        # Form
        form_layout = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_phone = QLineEdit()
        self.txt_email = QLineEdit()
        self.txt_address = QLineEdit()
        
        self.txt_name.setPlaceholderText("Nhập tên...")
        self.txt_phone.setPlaceholderText("Nhập số điện thoại...")

        form_layout.addRow("Tên khách hàng (*):", self.txt_name)
        form_layout.addRow("Số điện thoại (*):", self.txt_phone)
        form_layout.addRow("Email:", self.txt_email)
        form_layout.addRow("Địa chỉ:", self.txt_address)
        self.main_layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Lưu thông tin")
        self.btn_clear = QPushButton("Làm mới Form")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_clear.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_clear)
        self.main_layout.addLayout(btn_layout)

    def load_data(self):
        search = f"%{self.txt_search.text()}%"
        try:
            data = self.db.query("SELECT * FROM Customers WHERE CustomerName LIKE %s OR PhoneNumber LIKE %s", (search, search))
            self.table.setRowCount(0)
            for row, item in enumerate(data):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item['CustomerID'])))
                self.table.setItem(row, 1, QTableWidgetItem(item['CustomerName']))
                self.table.setItem(row, 2, QTableWidgetItem(item['PhoneNumber']))
                self.table.setItem(row, 3, QTableWidgetItem(item.get('Email', '')))
                self.table.setItem(row, 4, QTableWidgetItem(item.get('Address', '')))
        except Exception as e:
            self.show_message(str(e), True)

    def on_select(self):
        selected = self.table.selectedItems()
        if selected:
            self.current_id = selected[0].text()
            self.txt_name.setText(selected[1].text())
            self.txt_phone.setText(selected[2].text())
            self.txt_email.setText(selected[3].text())
            self.txt_address.setText(selected[4].text())

    def clear_form(self):
        self.current_id = None
        self.txt_name.clear()
        self.txt_phone.clear()
        self.txt_email.clear()
        self.txt_address.clear()
        self.table.clearSelection()

    def save_data(self):
        if not self.validate_inputs([self.txt_name, self.txt_phone]):
            self.show_message("Vui lòng điền đầy đủ các trường bắt buộc (*).", True)
            return

        name, phone = self.txt_name.text(), self.txt_phone.text()
        email, addr = self.txt_email.text(), self.txt_address.text()

        try:
            if self.current_id:
                self.db.execute("UPDATE Customers SET CustomerName=%s, PhoneNumber=%s, Email=%s, Address=%s WHERE CustomerID=%s", 
                                (name, phone, email, addr, self.current_id))
                self.show_message("Cập nhật khách hàng thành công!")
            else:
                self.db.execute("INSERT INTO Customers (CustomerName, PhoneNumber, Email, Address) VALUES (%s, %s, %s, %s)", 
                                (name, phone, email, addr))
                self.show_message("Thêm khách hàng thành công!")
            self.load_data()
            self.clear_form()
        except Exception as e:
            self.show_message(str(e), True)

# --- 3. Quản lý Bàn ---
class TableScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Quản lý Bàn")
        
        # Bộ lọc trạng thái bàn
        filter_layout = QHBoxLayout()
        self.cbo_filter_status = QComboBox()
        self.cbo_filter_status.addItems(["Tất cả", "Available", "Reserved", "Occupied", "Maintenance"])
        # Khi chọn đổi trạng thái lọc, tự động load lại dữ liệu
        self.cbo_filter_status.currentTextChanged.connect(self.load_data)
        
        filter_layout.addWidget(QLabel("Lọc theo trạng thái:"))
        filter_layout.addWidget(self.cbo_filter_status)
        filter_layout.addStretch()
        self.main_layout.addLayout(filter_layout)

        # Bảng
        self.table = self.setup_table(["ID", "Số Bàn", "Sức chứa", "Trạng thái"])
        self.main_layout.addWidget(self.table)

        btn_change_status = QPushButton("Đổi trạng thái (1 click)")
        btn_change_status.setStyleSheet("background-color: #9b59b6;")
        btn_change_status.clicked.connect(self.change_status)
        self.main_layout.addWidget(btn_change_status)

        form_layout = QHBoxLayout()
        self.txt_number = QLineEdit()
        self.txt_number.setPlaceholderText("Số bàn...")
        self.spin_capacity = QSpinBox()
        self.spin_capacity.setMinimum(1)
        self.cbo_status = QComboBox()
        self.cbo_status.addItems(["Available", "Reserved", "Occupied", "Maintenance"])
        
        btn_save = QPushButton("Thêm / Cập nhật")
        btn_save.clicked.connect(self.save_data)

        form_layout.addWidget(QLabel("Số bàn:"))
        form_layout.addWidget(self.txt_number)
        form_layout.addWidget(QLabel("Sức chứa:"))
        form_layout.addWidget(self.spin_capacity)
        form_layout.addWidget(QLabel("Trạng thái:"))
        form_layout.addWidget(self.cbo_status)
        form_layout.addWidget(btn_save)
        
        self.main_layout.addLayout(form_layout)

    def load_data(self):
        filter_status = self.cbo_filter_status.currentText()
        try:
            # Nếu chọn 'Tất cả' thì load hết, ngược lại thì lọc theo Status
            if filter_status == "Tất cả":
                data = self.db.query("SELECT * FROM Tables")
            else:
                data = self.db.query("SELECT * FROM Tables WHERE Status = %s", (filter_status,))
                
            self.table.setRowCount(0)
            colors = {"Available": "#2ecc71", "Reserved": "#f1c40f", "Occupied": "#e74c3c", "Maintenance": "#95a5a6"}
            for row, item in enumerate(data):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item['TableID'])))
                self.table.setItem(row, 1, QTableWidgetItem(str(item['TableNumber'])))
                self.table.setItem(row, 2, QTableWidgetItem(str(item['Capacity'])))
                
                status_item = QTableWidgetItem(item['Status'])
                color = colors.get(item['Status'], "#ffffff")
                status_item.setBackground(QColor(color))
                if item['Status'] in ['Occupied', 'Maintenance']:
                    status_item.setForeground(QColor("white"))
                
                self.table.setItem(row, 3, status_item)
        except Exception as e:
            self.show_message(str(e), True)

    def change_status(self):
        selected = self.table.selectedItems()
        if not selected:
            self.show_message("Vui lòng chọn 1 bàn để đổi trạng thái.", True)
            return
        tid = selected[0].text()
        current_status = selected[3].text()
        
        states = ["Available", "Reserved", "Occupied", "Maintenance"]
        next_state = states[(states.index(current_status) + 1) % len(states)]
        
        try:
            self.db.execute("UPDATE Tables SET Status=%s WHERE TableID=%s", (next_state, tid))
            self.load_data()
            self.show_message(f"Đã chuyển bàn sang {next_state}")
        except Exception as e:
            self.show_message(str(e), True)

    def save_data(self):
        if not self.validate_inputs([self.txt_number]):
            self.show_message("Vui lòng nhập Số bàn.", True)
            return
        num = self.txt_number.text()
        cap = self.spin_capacity.value()
        stat = self.cbo_status.currentText()
        try:
            # Check if exists
            exists = self.db.query("SELECT TableID FROM Tables WHERE TableNumber=%s", (num,))
            if exists:
                self.db.execute("UPDATE Tables SET Capacity=%s, Status=%s WHERE TableNumber=%s", (cap, stat, num))
                self.show_message("Cập nhật bàn thành công!")
            else:
                self.db.execute("INSERT INTO Tables (TableNumber, Capacity, Status) VALUES (%s, %s, %s)", (num, cap, stat))
                self.show_message("Thêm bàn thành công!")
            self.load_data()
        except Exception as e:
            self.show_message(str(e), True)

# --- 4. Thực đơn ---
class MenuScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Quản lý Thực Đơn")
        self.current_id = None
        
        self.table = self.setup_table(["ID", "Tên Món", "Danh mục", "Giá", "Mô tả", "Trạng thái"])
        self.table.itemSelectionChanged.connect(self.on_select)
        self.main_layout.addWidget(self.table)

        form_layout = QFormLayout()
        self.txt_name = QLineEdit()
        self.cbo_cat = QComboBox()
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setMaximum(10000000)
        self.spin_price.setSuffix(" đ")
        self.txt_desc = QLineEdit()
        self.chk_avail = QCheckBox("Còn hàng")
        self.chk_avail.setChecked(True)

        form_layout.addRow("Tên món (*):", self.txt_name)
        form_layout.addRow("Danh mục:", self.cbo_cat)
        form_layout.addRow("Giá bán:", self.spin_price)
        form_layout.addRow("Mô tả:", self.txt_desc)
        form_layout.addRow("", self.chk_avail)
        self.main_layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Lưu Món")
        btn_delete = QPushButton("Xóa Món")
        btn_clear = QPushButton("Làm mới")
        btn_delete.setStyleSheet("background-color: #e74c3c;")
        
        btn_save.clicked.connect(self.save_data)
        btn_delete.clicked.connect(self.delete_data)
        btn_clear.clicked.connect(self.clear_form)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_clear)
        self.main_layout.addLayout(btn_layout)

    def load_data(self):
        try:
            cats = self.db.query("SELECT * FROM MenuCategories")
            self.cbo_cat.clear()
            for c in cats:
                self.cbo_cat.addItem(c['CategoryName'], c['CategoryID'])

            data = self.db.query("""
                SELECT m.*, c.CategoryName 
                FROM MenuItems m 
                LEFT JOIN MenuCategories c ON m.CategoryID = c.CategoryID
                ORDER BY c.CategoryName, m.DishName
            """)
            self.table.setRowCount(0)
            for row, item in enumerate(data):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item['DishID'])))
                self.table.setItem(row, 1, QTableWidgetItem(item['DishName']))
                self.table.setItem(row, 2, QTableWidgetItem(item['CategoryName']))
                self.table.setItem(row, 3, QTableWidgetItem(f"{item['Price']:,.0f}"))
                self.table.setItem(row, 4, QTableWidgetItem(item.get('Description', '')))
                self.table.setItem(row, 5, QTableWidgetItem("Có" if item['IsAvailable'] else "Hết"))
        except Exception as e:
            self.show_message(str(e), True)

    def on_select(self):
        selected = self.table.selectedItems()
        if selected:
            self.current_id = selected[0].text()
            self.txt_name.setText(selected[1].text())
            # Find category index
            idx = self.cbo_cat.findText(selected[2].text())
            if idx >= 0: self.cbo_cat.setCurrentIndex(idx)
            self.spin_price.setValue(float(selected[3].text().replace(',', '')))
            self.txt_desc.setText(selected[4].text())
            self.chk_avail.setChecked(selected[5].text() == "Có")

    def clear_form(self):
        self.current_id = None
        self.txt_name.clear()
        self.txt_desc.clear()
        self.spin_price.setValue(0)
        self.chk_avail.setChecked(True)
        self.table.clearSelection()

    def save_data(self):
        if not self.validate_inputs([self.txt_name]):
            self.show_message("Vui lòng nhập tên món.", True)
            return
            
        name = self.txt_name.text()
        cat_id = self.cbo_cat.currentData()
        price = self.spin_price.value()
        desc = self.txt_desc.text()
        avail = 1 if self.chk_avail.isChecked() else 0

        try:
            if self.current_id:
                self.db.execute("UPDATE MenuItems SET CategoryID=%s, DishName=%s, Price=%s, Description=%s, IsAvailable=%s WHERE DishID=%s",
                                (cat_id, name, price, desc, avail, self.current_id))
                self.show_message("Cập nhật thành công!")
            else:
                self.db.execute("INSERT INTO MenuItems (CategoryID, DishName, Price, Description, IsAvailable) VALUES (%s, %s, %s, %s, %s)",
                                (cat_id, name, price, desc, avail))
                self.show_message("Thêm thành công!")
            self.load_data()
            self.clear_form()
        except Exception as e:
            self.show_message(str(e), True)

    def delete_data(self):
        if not self.current_id: return
        try:
            self.db.execute("DELETE FROM MenuItems WHERE DishID=%s", (self.current_id,))
            self.show_message("Đã xóa món ăn.")
            self.load_data()
            self.clear_form()
        except Exception as e:
            self.show_message("Không thể xóa món này do ràng buộc dữ liệu hóa đơn.", True)

# --- 5. Đặt bàn ---
class ReservationScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Quản lý Đặt Bàn")
        self.current_id = None

        # Filter
        filter_layout = QHBoxLayout()
        self.date_filter = QDateEdit(QDate.currentDate())
        self.date_filter.setCalendarPopup(True)
        self.date_filter.dateChanged.connect(self.load_data)
        filter_layout.addWidget(QLabel("Lọc theo ngày:"))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addStretch()
        self.main_layout.addLayout(filter_layout)

        self.table = self.setup_table(["ID", "Khách hàng", "Bàn", "Ngày", "Giờ", "Số khách", "Ghi chú", "Trạng thái"])
        self.table.itemSelectionChanged.connect(self.on_select)
        self.main_layout.addWidget(self.table)

        # Form
        form_layout = QGridLayout()
        self.cbo_cust = QComboBox()
        self.cbo_table = QComboBox()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.spin_guests = QSpinBox()
        self.spin_guests.setMinimum(1)
        self.txt_notes = QLineEdit()

        form_layout.addWidget(QLabel("Khách hàng:"), 0, 0)
        form_layout.addWidget(self.cbo_cust, 0, 1)
        form_layout.addWidget(QLabel("Bàn:"), 0, 2)
        form_layout.addWidget(self.cbo_table, 0, 3)
        form_layout.addWidget(QLabel("Ngày:"), 1, 0)
        form_layout.addWidget(self.date_edit, 1, 1)
        form_layout.addWidget(QLabel("Giờ:"), 1, 2)
        form_layout.addWidget(self.time_edit, 1, 3)
        form_layout.addWidget(QLabel("Số khách:"), 2, 0)
        form_layout.addWidget(self.spin_guests, 2, 1)
        form_layout.addWidget(QLabel("Ghi chú:"), 2, 2)
        form_layout.addWidget(self.txt_notes, 2, 3)
        self.main_layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Lưu Đặt Bàn")
        btn_confirm = QPushButton("Xác Nhận (Confirmed)")
        btn_cancel = QPushButton("Hủy (Cancelled)")
        btn_clear = QPushButton("Làm Mới")
        
        btn_confirm.setStyleSheet("background-color: #2ecc71;")
        btn_cancel.setStyleSheet("background-color: #e74c3c;")

        btn_save.clicked.connect(self.save_data)
        btn_confirm.clicked.connect(lambda: self.change_status('Confirmed'))
        btn_cancel.clicked.connect(lambda: self.change_status('Cancelled'))
        btn_clear.clicked.connect(self.clear_form)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_confirm)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_clear)
        self.main_layout.addLayout(btn_layout)

    def load_data(self):
        try:
            # Load comboboxes
            custs = self.db.query("SELECT CustomerID, CustomerName, PhoneNumber FROM Customers")
            self.cbo_cust.clear()
            for c in custs:
                self.cbo_cust.addItem(f"{c['CustomerName']} - {c['PhoneNumber']}", c['CustomerID'])

            tbls = self.db.query("SELECT TableID, TableNumber FROM Tables")
            self.cbo_table.clear()
            for t in tbls:
                self.cbo_table.addItem(f"Bàn {t['TableNumber']}", t['TableID'])

            # Load table
            filter_date = self.date_filter.date().toString("yyyy-MM-dd")
            data = self.db.query("""
                SELECT r.*, c.CustomerName, t.TableNumber 
                FROM Reservations r
                JOIN Customers c ON r.CustomerID = c.CustomerID
                JOIN Tables t ON r.TableID = t.TableID
                WHERE DATE(r.ReservationDate) = %s
                ORDER BY r.ReservationTime
            """, (filter_date,))
            
            self.table.setRowCount(0)
            for row, item in enumerate(data):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item['ReservationID'])))
                self.table.setItem(row, 1, QTableWidgetItem(item['CustomerName']))
                self.table.setItem(row, 2, QTableWidgetItem(str(item['TableNumber'])))
                self.table.setItem(row, 3, QTableWidgetItem(str(item['ReservationDate'])))
                self.table.setItem(row, 4, QTableWidgetItem(str(item['ReservationTime'])))
                self.table.setItem(row, 5, QTableWidgetItem(str(item['GuestCount'])))
                self.table.setItem(row, 6, QTableWidgetItem(item.get('Notes', '')))
                
                status_item = QTableWidgetItem(item['Status'])
                if item['Status'] == 'Confirmed':
                    status_item.setBackground(QColor('#d5f5e3'))
                elif item['Status'] == 'Cancelled':
                    status_item.setBackground(QColor('#fadbd8'))
                self.table.setItem(row, 7, status_item)
        except Exception as e:
            self.show_message(str(e), True)

    def on_select(self):
        selected = self.table.selectedItems()
        if selected:
            self.current_id = selected[0].text()
            # Set form values manually (Simplified for robust behavior)
            self.spin_guests.setValue(int(selected[5].text()))
            self.txt_notes.setText(selected[6].text())

    def clear_form(self):
        self.current_id = None
        self.txt_notes.clear()
        self.table.clearSelection()

    def save_data(self):
        if self.cbo_cust.currentData() is None or self.cbo_table.currentData() is None:
            self.show_message("Vui lòng chọn khách hàng và bàn.", True)
            return
            
        cid = self.cbo_cust.currentData()
        tid = self.cbo_table.currentData()
        rdate = self.date_edit.date().toString("yyyy-MM-dd")
        rtime = self.time_edit.time().toString("HH:mm:ss")
        guests = self.spin_guests.value()
        notes = self.txt_notes.text()

        try:
            if self.current_id:
                self.db.execute("""UPDATE Reservations SET CustomerID=%s, TableID=%s, ReservationDate=%s, 
                                ReservationTime=%s, GuestCount=%s, Notes=%s WHERE ReservationID=%s""",
                                (cid, tid, rdate, rtime, guests, notes, self.current_id))
                self.show_message("Cập nhật thành công!")
            else:
                self.db.execute("""INSERT INTO Reservations (CustomerID, TableID, ReservationDate, ReservationTime, GuestCount, Status, Notes) 
                                VALUES (%s, %s, %s, %s, %s, 'Pending', %s)""",
                                (cid, tid, rdate, rtime, guests, notes))
                self.db.execute("UPDATE Tables SET Status='Reserved' WHERE TableID=%s", (tid,))
                self.show_message("Thêm đặt bàn thành công!")
            self.load_data()
            self.clear_form()
        except Exception as e:
            self.show_message(str(e), True)

    def change_status(self, new_status):
        if not self.current_id:
            self.show_message("Vui lòng chọn một đặt bàn trước.", True)
            return
        try:
            if new_status == 'Confirmed':
                # ── Gọi sp_ConfirmReservation (IN: ReservationID, OUT: p_Result) ──
                # SP tự cập nhật Reservations.Status = 'Confirmed'
                # VÀ Tables.Status = 'Reserved' trong 1 TRANSACTION
                _, out_vals = self.db.call_proc_out(
                    "sp_ConfirmReservation",
                    in_args=[int(self.current_id)],
                    out_count=1
                )
                result_msg = str(out_vals[0]) if out_vals[0] else "Đã xác nhận"
                if "ERROR" in result_msg.upper():
                    self.show_message(f"Lỗi SP: {result_msg}", True)
                else:
                    self.show_message(f"✓ {result_msg}")
            else:
                # Cancelled / NoShow — cập nhật trực tiếp
                # trg_AfterReservationSeated sẽ tự set Tables.Status = 'Available'
                self.db.execute(
                    "UPDATE Reservations SET Status=%s WHERE ReservationID=%s",
                    (new_status, self.current_id)
                )
                self.show_message(f"Đã chuyển trạng thái thành {new_status}")
            self.load_data()
        except Exception as e:
            self.show_message(str(e), True)

# --- 6. Hóa đơn & Thanh toán ---
class InvoiceScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Hóa Đơn & Thanh Toán")
        self.invoice_items = [] # list of dicts: {'DishID', 'DishName', 'Price', 'Qty'}
        
        main_h_layout = QHBoxLayout()
        
        # Panel Trái: Cài đặt hóa đơn
        left_panel = QFrame()
        left_layout = QFormLayout(left_panel)
        self.cbo_cust = QComboBox()
        self.cbo_table = QComboBox()
        self.cbo_method = QComboBox()
        self.cbo_method.addItems(["Cash", "Credit Card", "Bank Transfer"])
        
        self.cbo_item = QComboBox()
        self.spin_qty = QSpinBox()
        self.spin_qty.setMinimum(1)
        btn_add_item = QPushButton("Thêm Món")
        btn_add_item.clicked.connect(self.add_item)

        left_layout.addRow("Khách hàng:", self.cbo_cust)
        left_layout.addRow("Bàn:", self.cbo_table)
        left_layout.addRow("Thanh toán:", self.cbo_method)
        left_layout.addRow(QLabel("--- Chọn Món ---"))
        left_layout.addRow("Món ăn:", self.cbo_item)
        left_layout.addRow("Số lượng:", self.spin_qty)
        left_layout.addRow("", btn_add_item)
        
        main_h_layout.addWidget(left_panel, 1)

        # Panel Phải: Chi tiết và Tính tiền
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        
        self.table = self.setup_table(["ID", "Tên Món", "Đơn giá", "SL", "Thành tiền"])
        btn_remove = QPushButton("Xóa món đã chọn")
        btn_remove.clicked.connect(self.remove_item)
        
        right_layout.addWidget(self.table)
        right_layout.addWidget(btn_remove, alignment=Qt.AlignmentFlag.AlignRight)

        # Tiền
        form_money = QFormLayout()
        self.lbl_subtotal = QLabel("0 đ")
        self.lbl_service = QLabel("0 đ (10%)")
        self.spin_discount = QDoubleSpinBox()
        self.spin_discount.setMaximum(10000000)
        self.spin_discount.valueChanged.connect(self.calculate_total)
        self.lbl_total = QLabel("0 đ")
        self.lbl_total.setStyleSheet("font-size: 20pt; font-weight: bold; color: #f39c12;")

        form_money.addRow("Tổng phụ:", self.lbl_subtotal)
        form_money.addRow("Phí DV (10%):", self.lbl_service)
        form_money.addRow("Chiết khấu (VND):", self.spin_discount)
        form_money.addRow("TỔNG TIỀN:", self.lbl_total)
        right_layout.addLayout(form_money)

        btn_pay = QPushButton("THANH TOÁN & IN HÓA ĐƠN")
        btn_pay.setStyleSheet("background-color: #2ecc71; font-size: 14pt; padding: 15px; font-weight: bold;")
        btn_pay.clicked.connect(self.process_payment)
        right_layout.addWidget(btn_pay)

        main_h_layout.addWidget(right_panel, 2)
        self.main_layout.addLayout(main_h_layout)

    def load_data(self):
        try:
            # 1. Load danh sách khách hàng
            custs = self.db.query("SELECT CustomerID, CustomerName FROM Customers")
            self.cbo_cust.clear()
            for c in custs: 
                self.cbo_cust.addItem(c['CustomerName'], c['CustomerID'])

            # 2. Load danh sách bàn
            tbls = self.db.query("SELECT TableID, TableNumber FROM Tables WHERE Status IN ('Occupied', 'Available')")
            self.cbo_table.clear()
            for t in tbls: 
                self.cbo_table.addItem(f"Bàn {t['TableNumber']}", t['TableID'])

            # 3. Load danh sách món ăn (Đã sửa lỗi IN rỗng ở đây)
            items = self.db.query("SELECT DishID, DishName, Price FROM MenuItems WHERE IsAvailable=1")
            self.cbo_item.clear()
            for i in items: 
                self.cbo_item.addItem(f"{i['DishName']} ({i['Price']:,.0f}đ)", {'id': i['DishID'], 'price': i['Price'], 'name': i['DishName']})
            
            self.invoice_items = []
            self.update_table()
            
        except Exception as e:
            # In ra màn hình console để debug dễ hơn
            print("LỖI TẠI LOAD_DATA INVOICE:", str(e))
            self.show_message(f"Lỗi tải dữ liệu: {str(e)}", True)
            
    def add_item(self):
        item_data = self.cbo_item.currentData()
        if not item_data: return
        
        qty = self.spin_qty.value()
        # Check if exists
        for item in self.invoice_items:
            if item['DishID'] == item_data['id']:
                item['Qty'] += qty
                self.update_table()
                return
        
        self.invoice_items.append({
            'DishID': item_data['id'],
            'DishName': item_data['name'],
            'Price': item_data['price'],
            'Qty': qty
        })
        self.update_table()

    def remove_item(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            del self.invoice_items[row]
            self.update_table()

    def update_table(self):
        self.table.setRowCount(0)
        subtotal = 0
        for row, item in enumerate(self.invoice_items):
            self.table.insertRow(row)
            total_price = item['Price'] * item['Qty']
            subtotal += total_price
            self.table.setItem(row, 0, QTableWidgetItem(str(item['DishID'])))
            self.table.setItem(row, 1, QTableWidgetItem(item['DishName']))
            self.table.setItem(row, 2, QTableWidgetItem(f"{item['Price']:,.0f}"))
            self.table.setItem(row, 3, QTableWidgetItem(str(item['Qty'])))
            self.table.setItem(row, 4, QTableWidgetItem(f"{total_price:,.0f}"))
        
        self.lbl_subtotal.setText(f"{subtotal:,.0f} đ")
        # Ép kiểu subtotal thành float trước khi nhân 0.1 để tránh lỗi Decimal
        service_charge = float(subtotal) * 0.1
        self.lbl_service.setText(f"{service_charge:,.0f} đ (10%)")
        self.subtotal_val = float(subtotal)
        self.service_val = service_charge
        self.calculate_total()

    def calculate_total(self):
        if not hasattr(self, 'subtotal_val'): return
        discount = self.spin_discount.value()
        total = self.subtotal_val + self.service_val - discount
        self.total_val = max(0, total)
        self.lbl_total.setText(f"{self.total_val:,.0f} đ")

    def process_payment(self):
        cid = self.cbo_cust.currentData()
        tid = self.cbo_table.currentData()
        method = self.cbo_method.currentText()

        if not cid or not tid or not self.invoice_items:
            self.show_message("Vui lòng chọn khách hàng, bàn và thêm món ăn!", is_error=True)
            return

        try:
            # Bước 1: Tạo hóa đơn nháp (Draft)
            invoice_id = self.db.execute(
                "INSERT INTO Invoices (CustomerID, TableID, PaymentMethod, Status) "
                "VALUES (%s, %s, %s, 'Draft')",
                (cid, tid, method)
            )

            # Bước 2: Thêm từng món ăn vào InvoiceItems
            for item in self.invoice_items:
                self.db.execute(
                    "INSERT INTO InvoiceItems (InvoiceID, DishID, Quantity, UnitPrice) "
                    "VALUES (%s, %s, %s, %s)",
                    (invoice_id, item['DishID'], item['Qty'], float(item['Price']))
                )

            # Bước 3: Gọi SP chốt hóa đơn (Database tự tính toán mọi thứ)
            self.db.call_proc_out(
                "sp_GenerateInvoice",
                in_args=[cid, tid, 0, method],  
                out_count=2                     
            )

            # BƯỚC 4 (FIX LỖI HIỂN THỊ 0đ): Truy vấn trực tiếp DB để lấy Tổng tiền
            # Vì thư viện mysql-connector lấy biến OUT hay bị xịt, ta hỏi thẳng DB cho chuẩn 100%!
            check_inv = self.db.query("SELECT TotalAmount FROM Invoices WHERE InvoiceID = %s", (invoice_id,))
            
            final_total = float(check_inv[0]['TotalAmount']) if check_inv else 0.0

            self.show_message(f"✓ Thanh toán thành công Hóa đơn #{invoice_id}! Tổng tiền: {final_total:,.0f} VND")
            
            # Reset lại UI sau khi thanh toán
            self.invoice_items = []
            self.update_table()
            self.spin_discount.setValue(0) # Reset ô chiết khấu

        except Exception as e:
            self.show_message(f"Lỗi thanh toán: {str(e)}", is_error=True)
            
# --- 7. Báo cáo ---
class ReportScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.lbl_title.setText("Báo Cáo Thống Kê")
        
        # Filter
        filter_layout = QHBoxLayout()
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)
        btn_view = QPushButton("Xem báo cáo")
        btn_view.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel("Từ ngày:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("Đến ngày:"))
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(btn_view)
        filter_layout.addStretch()
        self.main_layout.addLayout(filter_layout)

        # 5 Summary cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self.cards = {
            "count": self.create_summary("SỐ HÓA ĐƠN", "0"),
            "gross": self.create_summary("DOANH THU GROSS", "0"),
            "service": self.create_summary("PHÍ DỊCH VỤ", "0"),
            "discount": self.create_summary("CHIẾT KHẤU", "0"),
            "net": self.create_summary("DOANH THU NET", "0", True)
        }
        for c in self.cards.values(): stats_layout.addWidget(c)
        self.main_layout.addLayout(stats_layout)

        # Matplotlib Chart
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.main_layout.addWidget(self.canvas)

    def create_summary(self, title, value, highlight=False):
        frame = QFrame()
        
        # Giao diện phẳng (Flat Design) hiện đại, viền đáy tạo điểm nhấn
        bg_color = "#e74c3c" if highlight else "#ffffff"
        text_color = "#ffffff" if highlight else "#2c3e50"
        title_color = "#fadbd8" if highlight else "#7f8c8d"
        border = "none" if highlight else "1px solid #dcdde1"
        bottom_border = "4px solid #c0392b" if highlight else "4px solid #3498db"

        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: {border};
                border-bottom: {bottom_border};
                border-radius: 6px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color: {title_color}; font-size: 10pt; font-weight: bold;")
        
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {text_color};")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return frame

    def load_data(self):
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to   = self.date_to.date().toString("yyyy-MM-dd")

        try:
            # ── Gọi sp_RevenueReport (IN: StartDate, IN: EndDate) ────────────
            # SP trả về 2 result sets:
            #   [0] TotalInvoices, GrossSales, ServiceFees, TotalDiscounts, NetRevenue, AverageCheck
            #   [1..] DishName, QtySold, Revenue  (top 10)
            all_rows = self.db.call_proc("sp_RevenueReport", [d_from, d_to])

            # Result set 1: dòng đầu tiên là summary
            summary = all_rows[0] if all_rows else {}
            self.cards["count"].findChildren(QLabel)[1].setText(
                str(summary.get('TotalInvoices', 0)))
            self.cards["gross"].findChildren(QLabel)[1].setText(
                f"{float(summary.get('GrossSales') or 0):,.0f} đ")
            self.cards["service"].findChildren(QLabel)[1].setText(
                f"{float(summary.get('ServiceFees') or 0):,.0f} đ")
            self.cards["discount"].findChildren(QLabel)[1].setText(
                f"{float(summary.get('TotalDiscounts') or 0):,.0f} đ")
            self.cards["net"].findChildren(QLabel)[1].setText(
                f"{float(summary.get('NetRevenue') or 0):,.0f} đ")

            # Result set 2: các dòng còn lại là top-10 dishes
            chart_data = all_rows[1:] if len(all_rows) > 1 else []

            # FIX: Nếu mất result set 2, dùng câu lệnh SQL có điều kiện ngày tháng thay vì View ALL-TIME
            if not chart_data or 'DishName' not in (chart_data[0] if chart_data else {}):
                chart_data = self.db.query("""
                    SELECT mi.DishName, SUM(ii.Quantity) AS QtySold, SUM(ii.LineTotal) AS Revenue
                    FROM InvoiceItems ii
                    JOIN Invoices i ON ii.InvoiceID = i.InvoiceID
                    JOIN MenuItems mi ON ii.DishID = mi.DishID
                    WHERE i.Status = 'Paid' AND DATE(i.PaymentDate) BETWEEN %s AND %s
                    GROUP BY mi.DishName
                    ORDER BY Revenue DESC
                    LIMIT 10
                """, (d_from, d_to))

            names = [row['DishName'][:15] for row in chart_data]
            revs  = [float(row.get('Revenue', 0) or 0) for row in chart_data]
            
            self.figure.clear()
            ax = self.figure.add_subplot(111)

            bars = ax.bar(names, revs, color='#3498db', width=0.5,
                          edgecolor='none', zorder=3)

            ax.set_title("TOP 10 MÓN THEO DOANH THU", pad=15,
                         fontsize=12, fontweight='bold', color='#2c3e50')
            ax.set_ylabel("Doanh thu (VND)", fontsize=10, color='#7f8c8d')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#bdc3c7')
            ax.spines['bottom'].set_color('#bdc3c7')
            ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
            ax.tick_params(axis='x', rotation=25, labelsize=9, colors='#34495e')
            ax.tick_params(axis='y', labelsize=9, colors='#34495e')

            if revs:
                for bar in bars:
                    yval = bar.get_height()
                    if yval > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                yval + (max(revs) * 0.02),
                                f"{yval:,.0f}",
                                ha='center', va='bottom',
                                fontsize=8, color='#2c3e50')

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            self.show_message(str(e), True)