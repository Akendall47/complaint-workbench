CREATE TABLE staff(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, department TEXT);
CREATE TABLE cases(
  id TEXT PRIMARY KEY, received_at TEXT NOT NULL, source TEXT, product_kind TEXT,
  department TEXT, department_pred TEXT, department_conf REAL, department_true TEXT,
  type TEXT, type_conf REAL, type_true TEXT,
  state TEXT NOT NULL, owner_id TEXT, urgent INTEGER, urgent_manual INTEGER,
  return_count INTEGER DEFAULT 0, deadline TEXT, handed_over_at TEXT, accepted_at TEXT,
  duplicate_of TEXT, draft_state TEXT,
  customer_json TEXT, handover_json TEXT, handover_true_json TEXT,
  version INTEGER DEFAULT 0);
CREATE TABLE notes(
  id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, seq INTEGER,
  author TEXT, written_at TEXT, body TEXT);
CREATE TABLE claims(
  id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, seq INTEGER,
  text TEXT, quote TEXT, note_id INTEGER,
  inferred INTEGER, supported INTEGER, status TEXT, original_text TEXT);
CREATE TABLE events(
  id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, at TEXT NOT NULL,
  kind TEXT, from_state TEXT, to_state TEXT, actor_id TEXT);
CREATE TABLE policies(
  id TEXT PRIMARY KEY, section TEXT, title TEXT, body TEXT);
CREATE VIRTUAL TABLE policies_fts USING fts5(id, title, body);
CREATE TABLE audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor_id TEXT NOT NULL, role TEXT NOT NULL,
  case_id TEXT, action TEXT NOT NULL, detail_json TEXT, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);

CREATE INDEX idx_cases_state_deadline ON cases(state, deadline);
CREATE INDEX idx_cases_dept_type ON cases(department, type);
CREATE INDEX idx_cases_owner_state ON cases(owner_id, state);
CREATE INDEX idx_cases_received ON cases(received_at);
CREATE INDEX idx_cases_urgent ON cases(urgent);
CREATE INDEX idx_notes_case ON notes(case_id);
CREATE INDEX idx_claims_case ON claims(case_id);
CREATE INDEX idx_events_case ON events(case_id);
CREATE INDEX idx_events_at ON events(at);
CREATE INDEX idx_audit_case ON audit(case_id);

CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
