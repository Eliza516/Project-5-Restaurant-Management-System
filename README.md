# RESTAURANT MANAGEMENT SYSTEM (RMS)

A comprehensive, enterprise-grade Restaurant Management System. This project strictly implements the **Thick Database Paradigm**, shifting complex business logic, transactional integrity, and data analytics directly into the database layer rather than the application layer.

## 1. Core Design: Database Handles All Computations
Unlike traditional CRUD applications, the Python (PyQt6) client in this system acts merely as a thin presentation layer. All core business rules—including tax calculations, loyalty tier discounts, concurrency control, and state propagation—are executed via strictly encapsulated MySQL Database Objects.

## 2. Technical Architecture & Key Features

### 2.1. Advanced Database Objects 
The core engine of this application relies on robust MySQL components:
* **Triggers (Real-time State Management):** 
  * `trg_PreventDoubleBooking`: Prevents double-booking a table within a specific time window.
  * `trg_AfterReservationSeated`: Automatically propagates table states (Available to Occupied) based on reservation flow.
  * `trg_RecalcInvoiceOnItemInsert`: Auto-recalculates net totals upon line-item mutations to ensure data consistency.
* **Stored Procedures (ACID Transactions):** 
  * `sp_GenerateInvoice`: Handles multi-table mutations, dynamic service charges, and loyalty discounts in a single atomic transaction.
  * `sp_ConfirmReservation`: Executes strict state verification before confirming bookings.
  * `sp_RevenueReport`: Aggregates complex financial metrics and top-selling data for analytical plotting.
* **Materialized-style Views:** Optimized queries for Daily Dashboards, Available Tables, All-time Top-Selling Dishes, Monthly Revenue, and Customer Visit Frequencies.
* **User-Defined Functions (UDFs):** Encapsulated logic for currency formatting, dynamic service charges, and revenue-based loyalty discount tiers.

### 2.2. Role-Based Access Control (RBAC)
Database-level security mapped to specific operational privileges:
* **Admin:** Full DDL/DML access across the system.
* **Manager:** Read/Write access and user management capabilities.
* **Cashier:** Restricted to invoice generation, menu reads, and reservation updates.
* **Waiter:** Limited to table/menu viewing and reservation management.

### 2.3. Data Analytics & Reporting
The system integrates Python's **Pandas** and **Matplotlib** to ingest ResultSets directly from Stored Procedures. It dynamically renders real-time interactive financial charts and top-seller visualizations within the PyQt6 dashboard.

## 3. Technology Stack
* **Database:** MySQL 8.x (Advanced SQL)
* **Application & GUI:** Python 3.10+, PyQt6
* **Data Analytics:** Matplotlib, Pandas
* **Database Connector:** `mysql-connector-python`

## 4. Installation & Setup Guide

### 4.1. Database Initialization
Execute the SQL scripts located in the `database/` directory in the following strict order using MySQL Workbench or CLI:
1. `01_schema.sql`: Creates core tables, relations, and indexes.
2. `02_sample_data_510.sql`: Injects comprehensive sample data.
3. `03_advanced_objects.sql`: Deploys all Views, Functions, Procedures, and Triggers.

### 4.2. Application Setup
Clone the repository and install the required dependencies:
```bash
git clone [https://github.com/Eliza516/Project-5-Restaurant-Management-System.git](https://github.com/Eliza516/Project-5-Restaurant-Management-System.git)
cd Project-5-Restaurant-Management-System
pip install -r requirements.txt
```
### 4.3. Execution
Configure your MySQL credentials within database.py, then launch the application:

```bash
python main.py
```
Academic Context: Final Term Project - Database Management Systems
Developer: Phung Thi Thu Trang
Affiliation: Faculty of Data Science and Artificial Intelligence - National Economics University (NEU)
