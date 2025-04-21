-- データベースの作成
CREATE DATABASE IF NOT EXISTS news_summary;
USE news_summary;

-- ユーザーテーブルの作成
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- ユーザーの作成と権限の付与
CREATE USER IF NOT EXISTS 'tokuhara'@'%' IDENTIFIED BY 'dbpassword123';
GRANT ALL PRIVILEGES ON news_summary.* TO 'tokuhara'@'%';
FLUSH PRIVILEGES; 