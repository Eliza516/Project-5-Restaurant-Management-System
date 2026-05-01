import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QListWidget, QStackedWidget, QListWidgetItem, QLabel, QVBoxLayout)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

# Import screens
from views import (DashboardScreen, CustomerScreen, TableScreen, 
                   MenuScreen, ReservationScreen, InvoiceScreen, ReportScreen)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Restaurant Management System (DS66B - NEU)")
        self.resize(1100, 700)
        
        # Thiết lập Style Chung (Theme sáng pastel, hỗ trợ font Mac)
        self.setStyleSheet("""
            QWidget {
                font-family: Arial, -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 11pt;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLabel#title {
                font-size: 14pt;
                font-weight: bold;
                color: #34495e;
                padding-bottom: 10px;
                border-bottom: 2px solid #3498db;
            }
            /* Sidebar Styles */
            QListWidget {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
                outline: 0;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #f1f2f6;
            }
            QListWidget::item:selected {
                background-color: #eaf2f8;
                color: #2980b9;
                border-left: 5px solid #3498db;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #f1f2f6;
            }
            /* Buttons, Inputs, Tables */
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QLineEdit, QComboBox, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
                selection-background-color: #d6eaf8;
                selection-color: black;
                border: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                font-weight: bold;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #bdc3c7;
                border-right: 1px solid #bdc3c7;
            }
        """)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Left - Fixed 200px)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setIconSize(QSize(24, 24))
        
        nav_items = [
            "Dashboard", "Khách hàng", "Quản lý Bàn", 
            "Thực đơn", "Đặt bàn", "Hóa đơn & Thanh toán", "Báo cáo"
        ]
        
        for item in nav_items:
            list_item = QListWidgetItem(item)
            self.sidebar.addItem(list_item)
            
        main_layout.addWidget(self.sidebar)

        # 2. Stacked Widget (Right)
        self.stacked_widget = QStackedWidget()
        
        # Khởi tạo các màn hình
        self.screens = {
            0: DashboardScreen(),
            1: CustomerScreen(),
            2: TableScreen(),
            3: MenuScreen(),
            4: ReservationScreen(),
            5: InvoiceScreen(),
            6: ReportScreen()
        }
        
        for idx in range(7):
            self.stacked_widget.addWidget(self.screens[idx])
            
        main_layout.addWidget(self.stacked_widget)

        # Connect Sidebar to Stacked Widget
        self.sidebar.currentRowChanged.connect(self.change_screen)
        
        # Mặc định chọn Dashboard
        self.sidebar.setCurrentRow(0)

    def change_screen(self, index):
        self.stacked_widget.setCurrentIndex(index)
        # Tự động gọi hàm load_data nếu màn hình đó có
        screen = self.screens[index]
        if hasattr(screen, 'load_data'):
            screen.load_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Thiết lập Font hệ thống mặc định (Đã đổi sang Arial để tương thích máy Mac)
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())