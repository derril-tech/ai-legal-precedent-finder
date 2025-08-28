-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspaces table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspace memberships
CREATE TABLE workspace_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);

-- Cases table
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    citation VARCHAR(255) UNIQUE NOT NULL,
    docket_number VARCHAR(255),
    court VARCHAR(255) NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    case_name VARCHAR(500) NOT NULL,
    parties TEXT,
    outcome VARCHAR(100),
    decision_date DATE,
    opinion_date DATE,
    judge VARCHAR(255),
    s3_text_key VARCHAR(500),
    s3_pdf_key VARCHAR(500),
    text_content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Passages table (paragraph-level chunks)
CREATE TABLE passages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    passage_number INTEGER NOT NULL,
    section_type VARCHAR(50), -- 'holdings', 'reasoning', 'facts', 'dicta'
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(case_id, passage_number)
);

-- Case citations (edges between cases)
CREATE TABLE case_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citing_case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    cited_case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    treatment_type VARCHAR(50) NOT NULL, -- 'followed', 'overruled', 'distinguished'
    citation_text TEXT,
    context TEXT,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(citing_case_id, cited_case_id, treatment_type)
);

-- QA sessions
CREATE TABLE qa_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Answers table
CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    qa_session_id UUID NOT NULL REFERENCES qa_sessions(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    reasoning TEXT,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Citations in answers
CREATE TABLE answer_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    answer_id UUID NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    passage_id UUID REFERENCES passages(id),
    citation_text TEXT NOT NULL,
    relevance_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Precedent graph nodes
CREATE TABLE precedent_graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    node_type VARCHAR(50) DEFAULT 'case',
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Precedent graph edges
CREATE TABLE precedent_graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID NOT NULL REFERENCES precedent_graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES precedent_graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL, -- 'follows', 'overrules', 'distinguishes'
    weight DECIMAL(3,2) DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_node_id, target_node_id, edge_type)
);

-- Case summaries
CREATE TABLE case_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL, -- 'holdings', 'reasoning', 'dicta'
    summary_text TEXT NOT NULL,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(case_id, summary_type)
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_cases_workspace_id ON cases(workspace_id);
CREATE INDEX idx_cases_citation ON cases(citation);
CREATE INDEX idx_cases_court ON cases(court);
CREATE INDEX idx_cases_jurisdiction ON cases(jurisdiction);
CREATE INDEX idx_cases_decision_date ON cases(decision_date);

CREATE INDEX idx_passages_case_id ON passages(case_id);
CREATE INDEX idx_passages_section_type ON passages(section_type);
CREATE INDEX idx_passages_embedding ON passages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_case_citations_citing ON case_citations(citing_case_id);
CREATE INDEX idx_case_citations_cited ON case_citations(cited_case_id);
CREATE INDEX idx_case_citations_treatment ON case_citations(treatment_type);

CREATE INDEX idx_qa_sessions_workspace ON qa_sessions(workspace_id);
CREATE INDEX idx_qa_sessions_user ON qa_sessions(user_id);
CREATE INDEX idx_qa_sessions_status ON qa_sessions(status);

CREATE INDEX idx_answers_session ON answers(qa_session_id);

CREATE INDEX idx_answer_citations_answer ON answer_citations(answer_id);
CREATE INDEX idx_answer_citations_case ON answer_citations(case_id);

CREATE INDEX idx_audit_log_workspace ON audit_log(workspace_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Row Level Security (RLS) policies
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE passages ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE answer_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE precedent_graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE precedent_graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies (basic examples - will be enhanced with Casbin)
CREATE POLICY "Users can view their own organization" ON organizations
    FOR SELECT USING (id IN (
        SELECT organization_id FROM users WHERE id = current_setting('app.current_user_id')::UUID
    ));

CREATE POLICY "Users can view their workspace cases" ON cases
    FOR SELECT USING (workspace_id IN (
        SELECT workspace_id FROM workspace_memberships WHERE user_id = current_setting('app.current_user_id')::UUID
    ));

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_qa_sessions_updated_at BEFORE UPDATE ON qa_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
