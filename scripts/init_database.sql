-- ============================================================
-- 发票管理系统 - 数据库初始化脚本
-- ============================================================
-- 使用方法:
--   方式一: psql -U postgres -f init_database.sql
--   方式二: 在 pgAdmin 中执行此 SQL
-- ============================================================

-- 1. 创建数据库 (如果不存在)
SELECT 'CREATE DATABASE invoice_system'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'invoice_system')\gexec

-- 连接到目标数据库
\c invoice_system;

-- 2. 创建必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 3. 创建 schema
CREATE SCHEMA IF NOT EXISTS public;

-- 4. 授权
GRANT ALL PRIVILEGES ON DATABASE invoice_system TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ============================================================
-- 以下为表结构定义（仅供参考，SQLAlchemy会自动创建）
-- ============================================================

-- 发票主表
CREATE TABLE IF NOT EXISTS invoices (
    id BIGINT PRIMARY KEY,
    invoice_code VARCHAR(32),
    invoice_number VARCHAR(32),
    invoice_date TIMESTAMP,
    check_code VARCHAR(64),
    invoice_type VARCHAR(32),
    seller_name VARCHAR(256),
    seller_tax_id VARCHAR(64),
    seller_address VARCHAR(512),
    seller_bank VARCHAR(512),
    buyer_name VARCHAR(256),
    buyer_tax_id VARCHAR(64),
    buyer_address VARCHAR(512),
    buyer_bank VARCHAR(512),
    total_amount NUMERIC(18, 2),
    total_tax NUMERIC(18, 2),
    total_amount_with_tax NUMERIC(18, 2),
    remark TEXT,
    payee VARCHAR(64),
    reviewer VARCHAR(64),
    drawer VARCHAR(64),
    original_file_path VARCHAR(1024),
    original_file_name VARCHAR(256),
    file_format VARCHAR(16),
    file_size BIGINT,
    status VARCHAR(32) DEFAULT 'pending',
    is_duplicate BOOLEAN DEFAULT FALSE,
    is_valid BOOLEAN DEFAULT TRUE,
    verify_message TEXT,
    ocr_confidence NUMERIC(5, 4),
    parse_attempts INTEGER DEFAULT 0,
    archived_path VARCHAR(1024),
    archived_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发票明细表
CREATE TABLE IF NOT EXISTS invoice_items (
    id BIGINT PRIMARY KEY,
    invoice_id BIGINT REFERENCES invoices(id) ON DELETE CASCADE,
    item_no INTEGER,
    item_name VARCHAR(512),
    specification VARCHAR(256),
    unit VARCHAR(64),
    quantity NUMERIC(18, 4),
    unit_price NUMERIC(18, 6),
    amount NUMERIC(18, 2),
    tax_rate NUMERIC(5, 4),
    tax_amount NUMERIC(18, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 异步任务跟踪表
CREATE TABLE IF NOT EXISTS invoice_tasks (
    id BIGINT PRIMARY KEY,
    invoice_id BIGINT REFERENCES invoices(id) ON DELETE CASCADE,
    celery_task_id VARCHAR(64),
    task_type VARCHAR(64),
    status VARCHAR(32) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    result_data TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_code ON invoices(invoice_code);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_seller_tax_id ON invoices(seller_tax_id);
CREATE INDEX IF NOT EXISTS idx_invoices_buyer_tax_id ON invoices(buyer_tax_id);
CREATE INDEX IF NOT EXISTS idx_invoices_total_amount ON invoices(total_amount_with_tax);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_is_duplicate ON invoices(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_invoices_is_valid ON invoices(is_valid);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_updated_at ON invoices(updated_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_unique ON invoices(invoice_code, invoice_number, total_amount_with_tax);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);

CREATE INDEX IF NOT EXISTS idx_invoice_tasks_invoice_id ON invoice_tasks(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_tasks_celery_task_id ON invoice_tasks(celery_task_id);
CREATE INDEX IF NOT EXISTS idx_invoice_tasks_task_type ON invoice_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_invoice_tasks_status ON invoice_tasks(status);
CREATE INDEX IF NOT EXISTS idx_invoice_tasks_created_at ON invoice_tasks(created_at);

-- 完成提示
SELECT 'Database invoice_system initialized successfully!' AS message;
