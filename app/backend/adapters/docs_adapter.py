from __future__ import annotations

from dataclasses import dataclass

from app.backend import constants


@dataclass(frozen=True)
class DocsPaths:
	rfc_path: str
	matrix_path: str
	playbook_path: str
	handoff_path: str


def get_default_paths() -> DocsPaths:
	return DocsPaths(
		rfc_path=constants.DEFAULT_RFC_PATH,
		matrix_path=constants.DEFAULT_MATRIX_PATH,
		playbook_path=constants.DEFAULT_PLAYBOOK_PATH,
		handoff_path=constants.DEFAULT_HANDOFF_PATH,
	)

