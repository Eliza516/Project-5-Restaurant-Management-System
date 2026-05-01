-- ============================================================
-- PROJECT 05: RESTAURANT MANAGEMENT SYSTEM
-- Advanced Database Objects
-- ============================================================

USE restaurant_db;

-- ─────────────────────────────────────────────
-- VIEWS
-- ─────────────────────────────────────────────

-- 1. Daily Reservations Dashboard
CREATE OR REPLACE VIEW vw_DailyReservations AS
SELECT
    r.ReservationID,
    r.ReservationDate,
    r.ReservationTime,
    c.CustomerName,
    c.PhoneNumber,
    t.TableNumber,
    t.Capacity,
    r.GuestCount,
    r.Status,
    r.Notes
FROM Reservations r
JOIN Customers c ON r.CustomerID = c.CustomerID
JOIN Tables    t ON r.TableID    = t.TableID
ORDER BY r.ReservationDate, r.ReservationTime;

-- 2. Table Availability (shows only tables that are Available right now)
CREATE OR REPLACE VIEW vw_AvailableTables AS
SELECT
    t.TableID,
    t.TableNumber,
    t.Capacity,
    t.Location,
    t.Status,
    IFNULL(
        (SELECT COUNT(*) FROM Reservations r
         WHERE r.TableID = t.TableID
           AND r.ReservationDate = CURDATE()
           AND r.Status IN ('Pending','Confirmed')),
        0
    ) AS BookingsToday
FROM Tables t
WHERE t.Status = 'Available';

-- 3. Top-Selling Dishes (by revenue, all time)
CREATE OR REPLACE VIEW vw_TopSellingDishes AS
SELECT
    mi.DishID,
    mi.DishName,
    mc.CategoryName,
    mi.Price                                          AS CurrentPrice,
    SUM(ii.Quantity)                                  AS TotalQtySold,
    SUM(ii.LineTotal)                                 AS TotalRevenue
FROM InvoiceItems ii
JOIN MenuItems      mi ON ii.DishID    = mi.DishID
JOIN MenuCategories mc ON mi.CategoryID= mc.CategoryID
JOIN Invoices        i ON ii.InvoiceID  = i.InvoiceID
WHERE i.Status = 'Paid'
GROUP BY mi.DishID, mi.DishName, mc.CategoryName, mi.Price
ORDER BY TotalRevenue DESC;

-- 4. Monthly Revenue Summary
CREATE OR REPLACE VIEW vw_MonthlyRevenue AS
SELECT
    YEAR(PaymentDate)        AS RevenueYear,
    MONTH(PaymentDate)       AS RevenueMonth,
    COUNT(*)                 AS TotalInvoices,
    SUM(SubTotal)            AS GrossSales,
    SUM(ServiceCharge)       AS ServiceFees,
    SUM(DiscountAmount)      AS TotalDiscounts,
    SUM(TotalAmount)         AS NetRevenue
FROM Invoices
WHERE Status = 'Paid'
GROUP BY YEAR(PaymentDate), MONTH(PaymentDate)
ORDER BY RevenueYear DESC, RevenueMonth DESC;

-- 5. Customer Visit Frequency
CREATE OR REPLACE VIEW vw_CustomerVisits AS
SELECT
    c.CustomerID,
    c.CustomerName,
    c.PhoneNumber,
    COUNT(DISTINCT i.InvoiceID) AS TotalVisits,
    SUM(i.TotalAmount)          AS TotalSpend,
    MAX(i.PaymentDate)          AS LastVisit
FROM Customers c
LEFT JOIN Invoices i ON c.CustomerID = i.CustomerID AND i.Status = 'Paid'
GROUP BY c.CustomerID, c.CustomerName, c.PhoneNumber
ORDER BY TotalSpend DESC;

-- ─────────────────────────────────────────────
-- USER-DEFINED FUNCTIONS
-- ─────────────────────────────────────────────

DELIMITER $$

-- 1. Calculate Service Charge (10 % of subtotal by default)
CREATE FUNCTION IF NOT EXISTS fn_ServiceCharge(p_SubTotal DECIMAL(10,2), p_RatePercent DECIMAL(5,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    RETURN ROUND(p_SubTotal * p_RatePercent / 100, 0);
END$$

-- 2. Apply loyalty discount based on total spend tier
CREATE FUNCTION IF NOT EXISTS fn_LoyaltyDiscount(p_TotalSpend DECIMAL(12,2))
RETURNS DECIMAL(5,2)  -- returns discount % (0-15)
DETERMINISTIC
BEGIN
    DECLARE v_Rate DECIMAL(5,2);
    IF    p_TotalSpend >= 5000000 THEN SET v_Rate = 15.00;
    ELSEIF p_TotalSpend >= 2000000 THEN SET v_Rate = 10.00;
    ELSEIF p_TotalSpend >= 1000000 THEN SET v_Rate = 5.00;
    ELSE                                 SET v_Rate = 0.00;
    END IF;
    RETURN v_Rate;
END$$

-- 3. Format Vietnamese currency
CREATE FUNCTION IF NOT EXISTS fn_FormatVND(p_Amount DECIMAL(12,2))
RETURNS VARCHAR(30)
DETERMINISTIC
BEGIN
    RETURN CONCAT(FORMAT(p_Amount, 0), ' VND');
END$$

DELIMITER ;

-- ─────────────────────────────────────────────
-- STORED PROCEDURES
-- ─────────────────────────────────────────────

DELIMITER $$

-- 1. Confirm Reservation & update Table Status
CREATE PROCEDURE IF NOT EXISTS sp_ConfirmReservation(
    IN  p_ReservationID INT,
    OUT p_Result        VARCHAR(100)
)
BEGIN
    DECLARE v_TableID INT;
    DECLARE v_Status  VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_Result = 'ERROR: Transaction rolled back';
    END;

    START TRANSACTION;

    SELECT TableID, Status INTO v_TableID, v_Status
    FROM Reservations
    WHERE ReservationID = p_ReservationID
    FOR UPDATE;

    IF v_TableID IS NULL THEN
        SET p_Result = 'ERROR: Reservation not found';
        ROLLBACK;
    ELSEIF v_Status NOT IN ('Pending') THEN
        SET p_Result = CONCAT('ERROR: Cannot confirm reservation in status ', v_Status);
        ROLLBACK;
    ELSE
        UPDATE Reservations
        SET Status = 'Confirmed'
        WHERE ReservationID = p_ReservationID;

        UPDATE Tables
        SET Status = 'Reserved'
        WHERE TableID = v_TableID;

        COMMIT;
        SET p_Result = CONCAT('SUCCESS: Reservation #', p_ReservationID, ' confirmed');
    END IF;
END$$

-- 2. Generate Invoice from an active table
CREATE PROCEDURE IF NOT EXISTS sp_GenerateInvoice(
    IN  p_CustomerID    INT,
    IN  p_TableID       INT,
    IN  p_ReservationID INT,      -- nullable
    IN  p_PaymentMethod VARCHAR(20),
    OUT p_InvoiceID     INT,
    OUT p_Total         DECIMAL(10,2)
)
BEGIN
    DECLARE v_SubTotal   DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_Charge     DECIMAL(10,2);
    DECLARE v_Discount   DECIMAL(10,2);
    DECLARE v_TotalSpend DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_DiscRate   DECIMAL(5,2);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_InvoiceID = -1;
        SET p_Total     = 0;
    END;

    START TRANSACTION;

    -- 1. Tìm lại hóa đơn nháp mà Python vừa tạo ở bước trước
    SELECT InvoiceID INTO p_InvoiceID
    FROM Invoices
    WHERE CustomerID = p_CustomerID AND TableID = p_TableID AND Status = 'Draft'
    ORDER BY InvoiceID DESC LIMIT 1;

    -- Backup: Nếu không tìm thấy thì mới tạo mới
    IF p_InvoiceID IS NULL THEN
        INSERT INTO Invoices (CustomerID, TableID, ReservationID, PaymentMethod, Status)
        VALUES (p_CustomerID, p_TableID, NULLIF(p_ReservationID, 0), p_PaymentMethod, 'Draft');
        SET p_InvoiceID = LAST_INSERT_ID();
    END IF;

    -- 2. Tính toán chính xác tuyệt đối bằng Quantity * UnitPrice
    SELECT IFNULL(SUM(Quantity * UnitPrice), 0) INTO v_SubTotal
    FROM InvoiceItems
    WHERE InvoiceID = p_InvoiceID;

    -- 3. Tính phí dịch vụ (10%) và chiết khấu thân thiết
    SET v_Charge = fn_ServiceCharge(v_SubTotal, 10);

    SELECT IFNULL(SUM(TotalAmount), 0) INTO v_TotalSpend
    FROM Invoices
    WHERE CustomerID = p_CustomerID AND Status = 'Paid';

    SET v_DiscRate = fn_LoyaltyDiscount(v_TotalSpend);
    SET v_Discount = ROUND(v_SubTotal * v_DiscRate / 100, 0);

    SET p_Total = v_SubTotal + v_Charge - v_Discount;

    -- 4. Chốt hóa đơn
    UPDATE Invoices
    SET SubTotal       = v_SubTotal,
        ServiceCharge  = v_Charge,
        DiscountAmount = v_Discount,
        TotalAmount    = p_Total,
        PaymentMethod  = p_PaymentMethod,
        Status         = 'Paid',
        PaymentDate    = NOW()
    WHERE InvoiceID = p_InvoiceID;

    -- 5. Giải phóng bàn
    UPDATE Tables SET Status = 'Available' WHERE TableID = p_TableID;

    -- 6. Đóng Reservation nếu có
    IF p_ReservationID > 0 THEN
        UPDATE Reservations SET Status = 'Seated'
        WHERE ReservationID = p_ReservationID;
    END IF;

    COMMIT;
END$$

-- 3. Revenue report for a given period
CREATE PROCEDURE IF NOT EXISTS sp_RevenueReport(
    IN p_StartDate DATE,
    IN p_EndDate   DATE
)
BEGIN
    -- Summary line
    SELECT
        COUNT(*)                AS TotalInvoices,
        SUM(SubTotal)           AS GrossSales,
        SUM(ServiceCharge)      AS ServiceFees,
        SUM(DiscountAmount)     AS TotalDiscounts,
        SUM(TotalAmount)        AS NetRevenue,
        AVG(TotalAmount)        AS AverageCheck
    FROM Invoices
    WHERE Status = 'Paid'
      AND DATE(PaymentDate) BETWEEN p_StartDate AND p_EndDate;

    -- Per-dish breakdown
    SELECT
        mi.DishName,
        SUM(ii.Quantity)  AS QtySold,
        SUM(ii.LineTotal) AS Revenue
    FROM InvoiceItems ii
    JOIN Invoices  i  ON ii.InvoiceID  = i.InvoiceID
    JOIN MenuItems mi ON ii.DishID     = mi.DishID
    WHERE i.Status = 'Paid'
      AND DATE(i.PaymentDate) BETWEEN p_StartDate AND p_EndDate
    GROUP BY mi.DishName
    ORDER BY Revenue DESC
    LIMIT 10;
END$$

DELIMITER ;

-- ─────────────────────────────────────────────
-- TRIGGERS
-- ─────────────────────────────────────────────

DELIMITER $$

-- 1. Auto-set table to 'Occupied' when reservation becomes Seated
CREATE TRIGGER trg_AfterReservationSeated
AFTER UPDATE ON Reservations
FOR EACH ROW
BEGIN
    IF NEW.Status = 'Seated' AND OLD.Status <> 'Seated' THEN
        UPDATE Tables SET Status = 'Occupied' WHERE TableID = NEW.TableID;
    END IF;

    IF NEW.Status = 'Cancelled' AND OLD.Status IN ('Confirmed','Pending') THEN
        UPDATE Tables SET Status = 'Available' WHERE TableID = NEW.TableID;
    END IF;
END$$

-- 2. Prevent double-booking the same table in the same time slot (±90 min)
CREATE TRIGGER trg_PreventDoubleBooking
BEFORE INSERT ON Reservations
FOR EACH ROW
BEGIN
    DECLARE v_Conflict INT;

    SELECT COUNT(*) INTO v_Conflict
    FROM Reservations
    WHERE TableID          = NEW.TableID
      AND ReservationDate  = NEW.ReservationDate
      AND Status NOT IN ('Cancelled','NoShow')
      AND ABS(TIMESTAMPDIFF(MINUTE,
              CONCAT(NEW.ReservationDate,' ',NEW.ReservationTime),
              CONCAT(ReservationDate,' ',ReservationTime))) < 90;

    IF v_Conflict > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Table already booked within 90 minutes of this slot';
    END IF;
END$$

-- 3. Auto-recalculate invoice totals when a line item is inserted/updated
CREATE TRIGGER trg_RecalcInvoiceOnItemInsert
AFTER INSERT ON InvoiceItems
FOR EACH ROW
BEGIN
    UPDATE Invoices i
    SET SubTotal = (
            SELECT IFNULL(SUM(LineTotal),0)
            FROM InvoiceItems WHERE InvoiceID = NEW.InvoiceID
        ),
        TotalAmount = (
            SELECT IFNULL(SUM(LineTotal),0)
            FROM InvoiceItems WHERE InvoiceID = NEW.InvoiceID
        ) + ServiceCharge - DiscountAmount
    WHERE i.InvoiceID = NEW.InvoiceID;
END$$

DELIMITER ;

-- ─────────────────────────────────────────────
-- MYSQL DATABASE SECURITY
-- (Run as root/admin)
-- ─────────────────────────────────────────────

-- Admin: full access
CREATE USER IF NOT EXISTS 'rms_admin'@'localhost'   IDENTIFIED BY 'Admin@Rms2026!';
GRANT ALL PRIVILEGES ON restaurant_db.* TO 'rms_admin'@'localhost';

-- Manager: read/write + manage users (no DROP)
CREATE USER IF NOT EXISTS 'rms_manager'@'localhost' IDENTIFIED BY 'Mgr@Rms2026!';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON restaurant_db.* TO 'rms_manager'@'localhost';

-- Cashier: generate invoices, read menus & reservations
CREATE USER IF NOT EXISTS 'rms_cashier'@'localhost' IDENTIFIED BY 'Cash@Rms2026!';
GRANT SELECT ON restaurant_db.*                  TO 'rms_cashier'@'localhost';
GRANT INSERT, UPDATE ON restaurant_db.Invoices   TO 'rms_cashier'@'localhost';
GRANT INSERT, UPDATE ON restaurant_db.InvoiceItems TO 'rms_cashier'@'localhost';
GRANT EXECUTE ON restaurant_db.*                 TO 'rms_cashier'@'localhost';

-- Waiter: view tables/menus, create/update reservations only
CREATE USER IF NOT EXISTS 'rms_waiter'@'localhost' IDENTIFIED BY 'Wait@Rms2026!';
GRANT SELECT ON restaurant_db.Tables        TO 'rms_waiter'@'localhost';
GRANT SELECT ON restaurant_db.MenuItems     TO 'rms_waiter'@'localhost';
GRANT SELECT ON restaurant_db.MenuCategories TO 'rms_waiter'@'localhost';
GRANT SELECT, INSERT, UPDATE ON restaurant_db.Reservations TO 'rms_waiter'@'localhost';
GRANT SELECT ON restaurant_db.Customers     TO 'rms_waiter'@'localhost';

FLUSH PRIVILEGES;
