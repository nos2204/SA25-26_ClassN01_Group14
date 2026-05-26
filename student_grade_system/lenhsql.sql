-- Tạo database và bảng student cho hệ thống Quản lý Sinh viên
-- Chạy file này trong MySQL Workbench hoặc terminal MySQL

CREATE DATABASE IF NOT EXISTS qlsv;
USE qlsv;

CREATE TABLE IF NOT EXISTS student (
    Dep         VARCHAR(100)    NOT NULL,
    StudentID   VARCHAR(20)     PRIMARY KEY,
    Name        VARCHAR(100)    NOT NULL,
    Division    VARCHAR(20),
    Gender      VARCHAR(10),
    email       VARCHAR(100),
    DOB         VARCHAR(20),
    Grade       FLOAT,
    gpa         FLOAT           DEFAULT NULL,
    Credits     INT             DEFAULT 0,
    scholarship VARCHAR(5)      DEFAULT 'No'
);

-- Dữ liệu mẫu
INSERT INTO student (Dep, StudentID, Name, Division, Gender, email, DOB, Grade, Credits)
VALUES
    ('Computer Science', 'SV001', 'Nguyen Van A', 'Class1', 'Male',   'sva@example.com',  '2003-01-15', 8.5, 60),
    ('Computer Science', 'SV002', 'Tran Thi B',   'Class2', 'Female', 'svb@example.com',  '2003-03-20', 9.0, 80),
    ('Computer Engineering', 'SV003', 'Le Van C', 'Class1', 'Male',   'svc@example.com',  '2002-07-10', 5.5, 45),
    ('Electrical Engineering', 'SV004', 'Pham Thi D', 'Class3', 'Female', 'svd@example.com', '2003-09-05', 7.0, 90)
ON DUPLICATE KEY UPDATE Name = VALUES(Name);