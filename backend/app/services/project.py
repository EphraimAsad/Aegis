"""Project service for business logic."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.project import Project, ProjectStatus
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectScopeUpdateRequest,
    ProjectUpdateRequest,
)


class ProjectService:
    """Service for project operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def create(self, request: ProjectCreateRequest) -> Project:
        """
        Create a new project.

        Args:
            request: Project creation request

        Returns:
            The created project
        """
        project = Project(
            name=request.name,
            description=request.description,
            research_objective=request.research_objective,
            provider=request.provider,
            model=request.model,
            status=ProjectStatus.DRAFT,
            scope={},
        )

        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)

        return project

    async def get(self, project_id: int) -> Project:
        """
        Get a project by ID.

        Args:
            project_id: The project ID

        Returns:
            The project

        Raises:
            NotFoundError: If project not found
        """
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.clarification_questions))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise NotFoundError(
                f"Project with id {project_id} not found",
                details={"project_id": project_id},
            )

        return project

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: ProjectStatus | None = None,
    ) -> tuple[list[Project], int]:
        """
        List projects with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status

        Returns:
            Tuple of (projects, total_count)
        """
        query = select(Project).options(selectinload(Project.clarification_questions))

        if status:
            query = query.where(Project.status == status)

        # Count total
        count_query = select(func.count(Project.id))
        if status:
            count_query = count_query.where(Project.status == status)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Project.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        return projects, total

    async def update(self, project_id: int, request: ProjectUpdateRequest) -> Project:
        """
        Update a project.

        Args:
            project_id: The project ID
            request: Update request

        Returns:
            The updated project
        """
        project = await self.get(project_id)

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.flush()
        await self.db.refresh(project)

        return project

    async def update_scope(self, project_id: int, request: ProjectScopeUpdateRequest) -> Project:
        """
        Update project scope.

        Args:
            project_id: The project ID
            request: Scope update request

        Returns:
            The updated project
        """
        project = await self.get(project_id)
        project.scope = request.scope.model_dump()

        await self.db.flush()
        await self.db.refresh(project)

        return project

    async def update_status(self, project_id: int, status: ProjectStatus) -> Project:
        """
        Update project status.

        Args:
            project_id: The project ID
            status: New status

        Returns:
            The updated project

        Raises:
            ValidationError: If status transition is invalid
        """
        project = await self.get(project_id)

        # Validate status transitions
        valid_transitions = {
            ProjectStatus.DRAFT: [ProjectStatus.CLARIFYING, ProjectStatus.ARCHIVED],
            ProjectStatus.CLARIFYING: [ProjectStatus.READY, ProjectStatus.DRAFT, ProjectStatus.ARCHIVED],
            ProjectStatus.READY: [ProjectStatus.ACTIVE, ProjectStatus.CLARIFYING, ProjectStatus.ARCHIVED],
            ProjectStatus.ACTIVE: [ProjectStatus.COMPLETED, ProjectStatus.READY, ProjectStatus.ARCHIVED],
            ProjectStatus.COMPLETED: [ProjectStatus.ARCHIVED, ProjectStatus.ACTIVE],
            ProjectStatus.ARCHIVED: [ProjectStatus.DRAFT],
        }

        if status not in valid_transitions.get(project.status, []):
            raise ValidationError(
                f"Invalid status transition from {project.status} to {status}",
                details={
                    "current_status": project.status,
                    "requested_status": status,
                    "valid_transitions": valid_transitions.get(project.status, []),
                },
            )

        # Additional validation for transitioning to READY
        if status == ProjectStatus.READY:
            if project.unanswered_questions_count > 0:
                raise ValidationError(
                    "Cannot mark project as ready while there are unanswered clarification questions",
                    details={"unanswered_questions": project.unanswered_questions_count},
                )

        project.status = status

        await self.db.flush()
        await self.db.refresh(project)

        return project

    async def delete(self, project_id: int) -> None:
        """
        Delete a project.

        Args:
            project_id: The project ID
        """
        project = await self.get(project_id)
        await self.db.delete(project)
        await self.db.flush()

    async def start_clarification(self, project_id: int) -> Project:
        """
        Start the clarification process for a project.

        Generates clarification questions and updates status.

        Args:
            project_id: The project ID

        Returns:
            The updated project
        """
        project = await self.get(project_id)

        if project.status not in [ProjectStatus.DRAFT, ProjectStatus.CLARIFYING]:
            raise ValidationError(
                f"Cannot start clarification for project in {project.status} status",
                details={"current_status": project.status},
            )

        # Update status
        project.status = ProjectStatus.CLARIFYING

        await self.db.flush()
        await self.db.refresh(project)

        return project
