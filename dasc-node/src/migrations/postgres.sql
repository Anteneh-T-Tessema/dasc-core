-- DASC-Core Enterprise Ledger Schema for PostgreSQL
-- Optimized for high-throughput bitemporal audit trails

CREATE TABLE IF NOT EXISTS dasc_ledger (
    id BIGSERIAL PRIMARY KEY,
    intent_id UUID NOT NULL,
    actor_agent TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    reason_codes JSONB DEFAULT '[]'::JSONB,
    intent_json JSONB NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    previous_hash CHAR(64) NOT NULL,
    record_hash CHAR(64) NOT NULL,
    
    -- Indices for high-performance dashboard querying
    CONSTRAINT status_check CHECK (status IN ('COMMIT', 'REJECT', 'ESCALATE'))
);

CREATE INDEX idx_intent_id ON dasc_ledger(intent_id);
CREATE INDEX idx_status ON dasc_ledger(status);
CREATE INDEX idx_timestamp ON dasc_ledger(timestamp DESC);

COMMENT ON TABLE dasc_ledger IS 'Immutable, hash-chained bitemporal ledger for DASC safety decisions.';
