-- Migration 007: Create contract_templates table
-- Template Library - Pre-built Indian contract templates paired with playbooks

CREATE TABLE IF NOT EXISTS contract_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'custom',
    template_content TEXT,  -- Full DOCX content stored as base64 or plain text
    paired_playbook_id UUID REFERENCES playbooks(id) ON DELETE SET NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON contract_templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_paired_playbook ON contract_templates(paired_playbook_id);
CREATE INDEX IF NOT EXISTS idx_templates_is_premium ON contract_templates(is_premium);
