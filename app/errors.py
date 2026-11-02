"""Excepciones de dominio. La UI las muestra como notificación; la API, como HTTP."""

from __future__ import annotations


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class InvalidInput(DomainError):
    status_code = 422
