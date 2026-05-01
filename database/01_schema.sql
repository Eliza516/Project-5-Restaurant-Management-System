-- ============================================================
-- PROJECT 05: RESTAURANT MANAGEMENT SYSTEM
-- Database: MySQL
-- Author  : DS66B Group 2
-- Version : 1.0  |  Spring 2026
-- ============================================================

CREATE DATABASE IF NOT EXISTS restaurant_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE restaurant_db;

-- ─────────────────────────────────────────────
-- CORE TABLES
-- ─────────────────────────────────────────────

CREATE TABLE Customers (
    CustomerID   INT          NOT NULL AUTO_INCREMENT,
    CustomerName VARCHAR(100) NOT NULL,
    PhoneNumber  VARCHAR(20)  NOT NULL UNIQUE,
    Email        VARCHAR(100),
    Address      VARCHAR(255),
    CreatedAt    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_customers PRIMARY KEY (CustomerID)
);

CREATE TABLE Tables (
    TableID      INT         NOT NULL AUTO_INCREMENT,
    TableNumber  VARCHAR(10) NOT NULL UNIQUE,
    Capacity     TINYINT     NOT NULL DEFAULT 4,
    Location     VARCHAR(50)          DEFAULT 'Main Hall',
    Status       ENUM('Available','Reserved','Occupied','Maintenance')
                             NOT NULL DEFAULT 'Available',
    CONSTRAINT pk_tables PRIMARY KEY (TableID)
);

CREATE TABLE MenuCategories (
    CategoryID   INT         NOT NULL AUTO_INCREMENT,
    CategoryName VARCHAR(50) NOT NULL UNIQUE,
    CONSTRAINT pk_menu_categories PRIMARY KEY (CategoryID)
);

CREATE TABLE MenuItems (
    DishID       INT            NOT NULL AUTO_INCREMENT,
    CategoryID   INT            NOT NULL,
    DishName     VARCHAR(100)   NOT NULL,
    Description  TEXT,
    Price        DECIMAL(10,2)  NOT NULL CHECK (Price >= 0),
    IsAvailable  BOOLEAN        NOT NULL DEFAULT TRUE,
    ImageURL     VARCHAR(255),
    CreatedAt    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_menu_items  PRIMARY KEY (DishID),
    CONSTRAINT fk_dish_cat    FOREIGN KEY (CategoryID)
        REFERENCES MenuCategories(CategoryID) ON DELETE RESTRICT
);

CREATE TABLE Reservations (
    ReservationID   INT      NOT NULL AUTO_INCREMENT,
    CustomerID      INT      NOT NULL,
    TableID         INT      NOT NULL,
    ReservationDate DATE     NOT NULL,
    ReservationTime TIME     NOT NULL,
    GuestCount      TINYINT  NOT NULL CHECK (GuestCount > 0),
    Status          ENUM('Pending','Confirmed','Seated','Cancelled','NoShow')
                             NOT NULL DEFAULT 'Pending',
    Notes           TEXT,
    CreatedAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_reservations PRIMARY KEY (ReservationID),
    CONSTRAINT fk_res_customer FOREIGN KEY (CustomerID)
        REFERENCES Customers(CustomerID) ON DELETE RESTRICT,
    CONSTRAINT fk_res_table    FOREIGN KEY (TableID)
        REFERENCES Tables(TableID) ON DELETE RESTRICT
);

CREATE TABLE Invoices (
    InvoiceID      INT           NOT NULL AUTO_INCREMENT,
    CustomerID     INT           NOT NULL,
    TableID        INT           NOT NULL,
    ReservationID  INT,
    SubTotal       DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ServiceCharge  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    DiscountAmount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    TotalAmount    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PaymentMethod  ENUM('Cash','Card','Transfer','Voucher') DEFAULT 'Cash',
    PaymentDate    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Status         ENUM('Draft','Paid','Voided') NOT NULL DEFAULT 'Draft',
    CONSTRAINT pk_invoices     PRIMARY KEY (InvoiceID),
    CONSTRAINT fk_inv_customer FOREIGN KEY (CustomerID)
        REFERENCES Customers(CustomerID) ON DELETE RESTRICT,
    CONSTRAINT fk_inv_table    FOREIGN KEY (TableID)
        REFERENCES Tables(TableID) ON DELETE RESTRICT,
    CONSTRAINT fk_inv_res      FOREIGN KEY (ReservationID)
        REFERENCES Reservations(ReservationID) ON DELETE SET NULL
);

CREATE TABLE InvoiceItems (
    ItemID      INT           NOT NULL AUTO_INCREMENT,
    InvoiceID   INT           NOT NULL,
    DishID      INT           NOT NULL,
    Quantity    SMALLINT      NOT NULL CHECK (Quantity > 0),
    UnitPrice   DECIMAL(10,2) NOT NULL,
    LineTotal   DECIMAL(10,2) GENERATED ALWAYS AS (Quantity * UnitPrice) STORED,
    CONSTRAINT pk_invoice_items  PRIMARY KEY (ItemID),
    CONSTRAINT fk_ii_invoice     FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID) ON DELETE CASCADE,
    CONSTRAINT fk_ii_dish        FOREIGN KEY (DishID)
        REFERENCES MenuItems(DishID) ON DELETE RESTRICT
);

-- ─────────────────────────────────────────────
-- USER MANAGEMENT (Security)
-- ─────────────────────────────────────────────

CREATE TABLE AppUsers (
    UserID       INT          NOT NULL AUTO_INCREMENT,
    Username     VARCHAR(50)  NOT NULL UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL,
    Role         ENUM('admin','manager','cashier','waiter') NOT NULL DEFAULT 'waiter',
    IsActive     BOOLEAN      NOT NULL DEFAULT TRUE,
    CreatedAt    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_app_users PRIMARY KEY (UserID)
);

-- ─────────────────────────────────────────────
-- INDEXES (Performance Optimisation)
-- ─────────────────────────────────────────────

-- Reservation lookups by date are the most frequent query
CREATE INDEX idx_res_date       ON Reservations(ReservationDate);
CREATE INDEX idx_res_customer   ON Reservations(CustomerID);
CREATE INDEX idx_res_table      ON Reservations(TableID);
CREATE INDEX idx_res_status     ON Reservations(Status);

-- Dish search by name / availability
CREATE INDEX idx_dish_name      ON MenuItems(DishName);
CREATE INDEX idx_dish_available ON MenuItems(IsAvailable);
CREATE INDEX idx_dish_category  ON MenuItems(CategoryID);

-- Invoice lookups
CREATE INDEX idx_inv_date       ON Invoices(PaymentDate);
CREATE INDEX idx_inv_customer   ON Invoices(CustomerID);
CREATE INDEX idx_inv_status     ON Invoices(Status);

-- Customer phone lookup
CREATE INDEX idx_cust_phone     ON Customers(PhoneNumber);
