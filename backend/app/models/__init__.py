"""SQLAlchemy models.

Import all models here to ensure they are registered with the Base metadata.
This is necessary for Alembic to detect them for migrations.
"""

from app.db.base import Base

# Import models here as they are created
# from app.models.project import Project
# from app.models.document import Document

__all__ = ["Base"]
