-- Migration 027: Add missing columns to document_risks for batch finding persistence
-- These columns store the full finding metadata from the analysis pipeline

ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS rule_name VARCHAR(255);
ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS clause_type VARCHAR(100);
ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS redline_type VARCHAR(20);
ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS fix_reasoning TEXT;
ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS is_deal_breaker BOOLEAN DEFAULT FALSE;
ALTER TABLE document_risks ADD COLUMN IF NOT EXISTS confidence FLOAT;

CREATE INDEX IF NOT EXISTS idx_document_risks_doc_id ON document_risks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_risks_risk_level ON document_risks(risk_level);
CREATE INDEX IF NOT EXISTS idx_document_risks_rule_name ON document_risks(rule_name);
