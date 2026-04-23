"""Add mTLS certificate tables for agent identity and audit logging.

Revision ID: 20260322_0001
Revises: 20260119_0001
Create Date: 2026-03-22 00:00:00.000000

This migration adds two tables to support the mTLS transport layer security
feature (Issue #146):

- agent_certificates: Stores CA-signed certificates tied to agent DIDs,
  with lifecycle status (active/expired/revoked) and SHA-256 fingerprints
  for zero-trust freshness checks.

- certificate_audit_log: Immutable event log for all certificate issuance,
  renewal, and revocation events. Suitable for SIEM ingestion.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260322_0001"
down_revision: Union[str, None] = "20260119_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agent_certificates and certificate_audit_log tables."""

    # ------------------------------------------------------------------
    # agent_certificates
    # ------------------------------------------------------------------
    op.create_table(
        "agent_certificates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("agent_did", sa.String(255), nullable=False),
        sa.Column("cert_fingerprint", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column(
            "issued_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        comment="mTLS agent certificates tied to DIDs",
    )

    # Indexes for zero-trust freshness checks
    op.create_index(
        "idx_agent_certs_fingerprint",
        "agent_certificates",
        ["cert_fingerprint"],
    )
    op.create_index(
        "idx_agent_certs_status",
        "agent_certificates",
        ["status"],
    )
    op.create_index(
        "idx_agent_certs_agent_did",
        "agent_certificates",
        ["agent_did"],
    )

    # Auto-update trigger for updated_at
    op.execute("""
        CREATE TRIGGER update_agent_certificates_updated_at
        BEFORE UPDATE ON agent_certificates
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # ------------------------------------------------------------------
    # certificate_audit_log
    # ------------------------------------------------------------------
    op.create_table(
        "certificate_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("agent_did", sa.String(255), nullable=False),
        sa.Column("cert_fingerprint", sa.String(255), nullable=False),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        comment="Immutable audit log for certificate lifecycle events (SIEM)",
    )

    # Indexes for audit queries
    op.create_index(
        "idx_cert_audit_agent_did",
        "certificate_audit_log",
        ["agent_did"],
    )
    op.create_index(
        "idx_cert_audit_fingerprint",
        "certificate_audit_log",
        ["cert_fingerprint"],
    )
    op.create_index(
        "idx_cert_audit_event_type",
        "certificate_audit_log",
        ["event_type"],
    )
    op.create_index(
        "idx_cert_audit_created_at",
        "certificate_audit_log",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    """Remove mTLS certificate tables."""

    # Drop certificate_audit_log
    op.drop_index("idx_cert_audit_created_at", table_name="certificate_audit_log")
    op.drop_index("idx_cert_audit_event_type", table_name="certificate_audit_log")
    op.drop_index("idx_cert_audit_fingerprint", table_name="certificate_audit_log")
    op.drop_index("idx_cert_audit_agent_did", table_name="certificate_audit_log")
    op.drop_table("certificate_audit_log")

    # Drop agent_certificates
    op.execute(
        "DROP TRIGGER IF EXISTS update_agent_certificates_updated_at ON agent_certificates"
    )
    op.drop_index("idx_agent_certs_agent_did", table_name="agent_certificates")
    op.drop_index("idx_agent_certs_status", table_name="agent_certificates")
    op.drop_index("idx_agent_certs_fingerprint", table_name="agent_certificates")
    op.drop_table("agent_certificates")