import mysql.connector
from mysql.connector import Error


class DatabaseManager:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'rms_admin',
            'password': 'Admin@Rms2026!',
            'database': 'restaurant_db',
            'raise_on_warnings': True
        }
        self.conn = None

    def connect(self):
        try:
            if self.conn is None or not self.conn.is_connected():
                self.conn = mysql.connector.connect(**self.config)
            return True
        except Error as e:
            print(f"DB Connection Error: {e}")
            return False

    def disconnect(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def query(self, sql, params=None):
        """SELECT — trả về list[dict]."""
        if not self.connect():
            return []
        try:
            self.conn.rollback()
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            print(f"Database Query Error: {e}")
            return []

    def execute(self, sql, params=None):
        """INSERT / UPDATE / DELETE — trả về lastrowid."""
        if not self.connect():
            raise Exception("Không thể kết nối đến cơ sở dữ liệu.")
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params or ())
            self.conn.commit()
            last_row_id = cursor.lastrowid
            cursor.close()
            return last_row_id
        except Error as e:
            self.conn.rollback()
            raise Exception(f"Lỗi thực thi: {str(e)}")

    # ------------------------------------------------------------------
    # STORED PROCEDURE SUPPORT
    # ------------------------------------------------------------------

    def call_proc(self, proc_name, in_args=None):
        """
        Gọi stored procedure chỉ có IN parameters.
        Trả về list[dict] từ tất cả result sets.

        Ví dụ:
            rows = db.call_proc("sp_RevenueReport", ["2026-01-01", "2026-03-31"])
        """
        if not self.connect():
            raise Exception("Không thể kết nối đến cơ sở dữ liệu.")
        args = in_args or []
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, args)
            results = []
            for rs in cursor.stored_results():
                results.extend(rs.fetchall())
            self.conn.commit()
            return results
        except Error as e:
            self.conn.rollback()
            raise Exception(f"Lỗi stored procedure '{proc_name}': {str(e)}")
        finally:
            cursor.close()

    def call_proc_out(self, proc_name, in_args, out_count):
        """
        Gọi stored procedure có cả IN lẫn OUT parameters.
        Trả về (result_rows: list[dict], out_values: list).

        mysql-connector lưu OUT params vào session variables
        @_<proc_name>_<index> sau khi callproc() chạy xong.

        Ví dụ:
            rows, outs = db.call_proc_out(
                "sp_ConfirmReservation", [reservation_id], out_count=1
            )
            message = outs[0]   # giá trị OUT p_Result

            rows, outs = db.call_proc_out(
                "sp_GenerateInvoice",
                [customer_id, table_id, reservation_id, payment_method],
                out_count=2
            )
            invoice_id = outs[0]
            total      = outs[1]
        """
        if not self.connect():
            raise Exception("Không thể kết nối đến cơ sở dữ liệu.")

        # Placeholder cho OUT params — mysql-connector cần đủ số lượng args
        all_args = list(in_args) + [None] * out_count
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, all_args)
            results = []
            for rs in cursor.stored_results():
                results.extend(rs.fetchall())
            self.conn.commit()

            # Lấy giá trị OUT từ session variables
            out_values = []
            plain_cursor = self.conn.cursor()
            for i in range(len(in_args), len(in_args) + out_count):
                plain_cursor.execute(f"SELECT @_{proc_name}_{i} AS v")
                row = plain_cursor.fetchone()
                out_values.append(row[0] if row else None)
            plain_cursor.close()

            return results, out_values

        except Error as e:
            self.conn.rollback()
            raise Exception(f"Lỗi stored procedure '{proc_name}': {str(e)}")
        finally:
            cursor.close()