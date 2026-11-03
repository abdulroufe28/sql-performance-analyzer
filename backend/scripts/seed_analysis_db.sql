CREATE DATABASE IF NOT EXISTS sql_performance_analysis;
USE sql_performance_analysis;

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    status VARCHAR(30) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Seed Customers
INSERT INTO customers (id, name, email, city, created_at) VALUES
(1, 'Arun Kumar', 'arun@example.com', 'Chennai', NOW()),
(2, 'Rahul Kumar', 'rahul@example.com', 'Bangalore', NOW()),
(3, 'Priya Sharma', 'priya@example.com', 'Mumbai', NOW()),
(4, 'Karthik Raj', 'karthik@example.com', 'Hyderabad', NOW()),
(5, 'Meena Devi', 'meena@example.com', 'Delhi', NOW())
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- Seed Orders
INSERT INTO orders (id, customer_id, order_date, status, total_amount) VALUES
(1, 1, NOW(), 'COMPLETED', 1250.00),
(2, 1, NOW(), 'PENDING', 450.50),
(3, 2, NOW(), 'COMPLETED', 3200.00),
(4, 3, NOW(), 'PROCESSING', 150.00),
(5, 4, NOW(), 'COMPLETED', 890.00),
(6, 5, NOW(), 'CANCELLED', 210.00)
ON DUPLICATE KEY UPDATE status=VALUES(status);
