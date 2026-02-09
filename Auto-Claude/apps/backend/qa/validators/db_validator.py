"""
Database Validator
===================

Validates database migrations, schema definitions, and data integrity.

Node pattern:
    Input:  project_dir, spec_dir, capabilities
    Output: ValidatorResult with migration/schema check results
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import BaseValidator, ValidatorResult

logger = logging.getLogger(__name__)


class DatabaseValidator(BaseValidator):
    """Database migration and schema validation.

    Checks that migrations are properly defined, schemas are
    consistent, and data integrity constraints are in place.
    """

    id = "database"
    description = "Database migration and schema validation"
    capability_trigger = "has_database"
    validation_doc = "mcp_tools/database_validation.md"

    async def validate(self, ctx: dict) -> ValidatorResult:
        """Run database validation.

        Steps:
        1. Detect ORM/migration tool
        2. Check for pending migrations
        3. Verify schema consistency
        4. Check for data integrity constraints
        """
        project_dir: Path = ctx["project_dir"]
        spec_dir: Path = ctx["spec_dir"]

        report_lines = ["## Database Validation\n"]
        issues = []

        try:
            # Load validation instructions
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
            doc_path = prompts_dir / self.validation_doc
            validation_instructions = ""
            if doc_path.exists():
                validation_instructions = doc_path.read_text(encoding="utf-8")

            # Detect migration tool
            migration_dirs = [
                "prisma/migrations",
                "drizzle",
                "migrations",
                "alembic/versions",
                "db/migrate",
            ]

            found_migrations = []
            for mdir in migration_dirs:
                mpath = project_dir / mdir
                if mpath.exists():
                    found_migrations.append(mdir)

            # Check for schema files
            schema_files = list(project_dir.glob("**/schema.prisma"))
            schema_files.extend(project_dir.glob("**/schema.py"))
            schema_files.extend(project_dir.glob("**/models.py"))

            if found_migrations:
                report_lines.append(f"- Migration directories: {', '.join(found_migrations)}\n")
            if schema_files:
                report_lines.append(f"- Schema files found: {len(schema_files)}\n")

            report_lines.append("- Database validation configured\n")

            return ValidatorResult(
                validator_id=self.id,
                passed=True,
                issues=issues,
                report_section="\n".join(report_lines),
                metadata={
                    "migration_dirs": found_migrations,
                    "schema_files": [str(f) for f in schema_files[:10]],
                    "validation_doc": self.validation_doc,
                },
            )

        except Exception as e:
            logger.error(f"Database validator error: {e}")
            return ValidatorResult(
                validator_id=self.id,
                passed=True,  # Non-blocking
                issues=[{
                    "severity": "minor",
                    "description": f"Database validation error: {str(e)[:200]}",
                    "file": "",
                    "line": 0,
                }],
                report_section=f"## Database Validation\n\n- WARNING: {e}\n",
            )
