DEFAULT_RFC_PATH = "docs/oversight_assistant_rfc.md"
DEFAULT_MATRIX_PATH = "docs/requirements_trace_matrix.md"
DEFAULT_PLAYBOOK_PATH = "docs/patch_playbook.md"
DEFAULT_HANDOFF_PATH = "SESSION_HANDOFF.md"
DEFAULT_DB_PATH = "oversight_state.db"
APP_NAME = "Oversight Ops App"
APP_VERSION = "1.0.0"
DEFAULT_CORS_ALLOW_ORIGINS = [
	"http://localhost",
	"http://127.0.0.1",
	"http://localhost:3000",
]
DEFAULT_TRUSTED_HOSTS = [
	"127.0.0.1",
	"localhost",
	"testserver",
]
SQLITE_BUSY_TIMEOUT_MS = 5000

INVARIANT_ORDER = [
	"toolchain_ok",
	"parity",
	"no_orphan_must",
	"finding_integrity",
	"backlink_consistency",
	"blocker_pin",
	"state_integrity",
]

WAVE1_BLOCKERS = (
	"F-001",
	"F-002",
	"F-003",
	"F-004",
	"F-007",
	"F-009",
)
