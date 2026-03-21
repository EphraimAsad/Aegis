"""Project management endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.core.exceptions import NotFoundError, ValidationError
from app.dependencies import DbSessionDep
from app.models.clarification import ClarificationQuestion
from app.models.project import Project
from app.models.project import ProjectStatus as ModelProjectStatus
from app.schemas.clarification import (
    AnswerQuestionRequest,
    ClarificationQuestionResponse,
    ClarificationQuestionsListResponse,
    ClarificationStatusResponse,
    GenerateQuestionsRequest,
)
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetail,
    ProjectListResponse,
    ProjectScope,
    ProjectScopeUpdateRequest,
    ProjectStatus,
    ProjectStatusUpdateRequest,
    ProjectSummary,
    ProjectUpdateRequest,
)
from app.services.clarification import ClarificationService
from app.services.project import ProjectService

router = APIRouter()


# =============================================================================
# Project CRUD
# =============================================================================


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    db: DbSessionDep,
) -> ProjectDetail:
    """
    Create a new research project.

    The project starts in DRAFT status and needs clarification
    questions to be answered before research can begin.
    """
    service = ProjectService(db)
    project = await service.create(request)
    await db.commit()

    return _project_to_detail(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: DbSessionDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: ProjectStatus | None = Query(None, description="Filter by status"),
) -> ProjectListResponse:
    """
    List all projects with pagination.

    Optionally filter by project status.
    """
    service = ProjectService(db)

    # Convert schema status to model status if provided
    model_status = None
    if status:
        model_status = ModelProjectStatus(status.value)

    projects, total = await service.list(page, page_size, model_status)

    return ProjectListResponse(
        projects=[_project_to_summary(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: DbSessionDep,
) -> ProjectDetail:
    """
    Get a project by ID.

    Returns full project details including scope and configuration.
    """
    service = ProjectService(db)

    try:
        project = await service.get(project_id)
        return _project_to_detail(project)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: DbSessionDep,
) -> ProjectDetail:
    """
    Update a project's basic information.

    Does not update scope or status - use dedicated endpoints for those.
    """
    service = ProjectService(db)

    try:
        project = await service.update(project_id, request)
        await db.commit()
        return _project_to_detail(project)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: DbSessionDep,
) -> None:
    """
    Delete a project.

    This also deletes all associated clarification questions and data.
    """
    service = ProjectService(db)

    try:
        await service.delete(project_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


# =============================================================================
# Project Scope
# =============================================================================


@router.put("/{project_id}/scope", response_model=ProjectDetail)
async def update_project_scope(
    project_id: int,
    request: ProjectScopeUpdateRequest,
    db: DbSessionDep,
) -> ProjectDetail:
    """
    Update the project's research scope.

    The scope defines parameters like keywords, date ranges,
    disciplines, and other search filters.
    """
    service = ProjectService(db)

    try:
        project = await service.update_scope(project_id, request)
        await db.commit()
        return _project_to_detail(project)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


# =============================================================================
# Project Status
# =============================================================================


@router.put("/{project_id}/status", response_model=ProjectDetail)
async def update_project_status(
    project_id: int,
    request: ProjectStatusUpdateRequest,
    db: DbSessionDep,
) -> ProjectDetail:
    """
    Update the project's status.

    Valid transitions:
    - DRAFT -> CLARIFYING, ARCHIVED
    - CLARIFYING -> READY, DRAFT, ARCHIVED
    - READY -> ACTIVE, CLARIFYING, ARCHIVED
    - ACTIVE -> COMPLETED, READY, ARCHIVED
    - COMPLETED -> ARCHIVED, ACTIVE
    - ARCHIVED -> DRAFT
    """
    service = ProjectService(db)

    try:
        model_status = ModelProjectStatus(request.status.value)
        project = await service.update_status(project_id, model_status)
        await db.commit()
        return _project_to_detail(project)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message) from e


# =============================================================================
# Clarification Questions
# =============================================================================


@router.post("/{project_id}/clarify", response_model=ClarificationQuestionsListResponse)
async def start_clarification(
    project_id: int,
    db: DbSessionDep,
    request: GenerateQuestionsRequest | None = None,
) -> ClarificationQuestionsListResponse:
    """
    Start or continue the clarification process.

    Generates AI-powered clarification questions based on the
    research objective. Updates project status to CLARIFYING.
    """
    project_service = ProjectService(db)
    clarification_service = ClarificationService(db)

    try:
        # Get and update project status
        project = await project_service.start_clarification(project_id)

        # Generate questions
        force = request.force_regenerate if request else False
        questions = await clarification_service.generate_questions(project, force)

        await db.commit()

        answered = sum(1 for q in questions if q.is_answered)
        return ClarificationQuestionsListResponse(
            project_id=project_id,
            questions=[_question_to_response(q) for q in questions],
            total=len(questions),
            answered=answered,
            unanswered=len(questions) - answered,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{project_id}/questions", response_model=ClarificationQuestionsListResponse
)
async def get_clarification_questions(
    project_id: int,
    db: DbSessionDep,
) -> ClarificationQuestionsListResponse:
    """
    Get all clarification questions for a project.
    """
    # Verify project exists
    project_service = ProjectService(db)
    try:
        await project_service.get(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e

    clarification_service = ClarificationService(db)
    questions = await clarification_service.get_questions(project_id)

    answered = sum(1 for q in questions if q.is_answered)
    return ClarificationQuestionsListResponse(
        project_id=project_id,
        questions=[_question_to_response(q) for q in questions],
        total=len(questions),
        answered=answered,
        unanswered=len(questions) - answered,
    )


@router.put(
    "/{project_id}/questions/{question_id}",
    response_model=ClarificationQuestionResponse,
)
async def answer_clarification_question(
    project_id: int,
    question_id: int,
    request: AnswerQuestionRequest,
    db: DbSessionDep,
) -> ClarificationQuestionResponse:
    """
    Answer a clarification question.

    The answer will be used to refine the project scope
    if the question maps to a scope field.
    """
    clarification_service = ClarificationService(db)

    try:
        question = await clarification_service.answer_question(question_id, request)

        # Verify the question belongs to the project
        if question.project_id != project_id:
            raise HTTPException(
                status_code=404, detail="Question not found for this project"
            )

        await db.commit()
        return _question_to_response(question)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get(
    "/{project_id}/clarification-status", response_model=ClarificationStatusResponse
)
async def get_clarification_status(
    project_id: int,
    db: DbSessionDep,
) -> ClarificationStatusResponse:
    """
    Get the clarification status for a project.

    Shows how many questions have been answered and
    whether the project can proceed to research.
    """
    # Verify project exists
    project_service = ProjectService(db)
    try:
        await project_service.get(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e

    clarification_service = ClarificationService(db)
    status = await clarification_service.get_status(project_id)

    return ClarificationStatusResponse(**status)


# =============================================================================
# Helper functions
# =============================================================================


def _project_to_summary(project: Project) -> ProjectSummary:
    """Convert a Project model to a ProjectSummary schema."""
    return ProjectSummary(
        id=project.id,
        name=project.name,
        status=ProjectStatus(project.status.value),
        research_objective=project.research_objective,
        created_at=project.created_at,
        updated_at=project.updated_at,
        unanswered_questions=project.unanswered_questions_count,
    )


def _project_to_detail(project: Project) -> ProjectDetail:
    """Convert a Project model to a ProjectDetail schema."""
    scope = None
    if project.scope:
        scope = ProjectScope(**project.scope)

    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        research_objective=project.research_objective,
        status=ProjectStatus(project.status.value),
        scope=scope,
        provider=project.provider,
        model=project.model,
        max_results_per_source=project.max_results_per_source,
        sources_enabled=project.sources_enabled or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_scope_complete=project.is_scope_complete,
        unanswered_questions=project.unanswered_questions_count,
        is_ready_for_research=project.is_ready_for_research,
    )


def _question_to_response(
    question: ClarificationQuestion,
) -> ClarificationQuestionResponse:
    """Convert a ClarificationQuestion model to response schema."""
    from app.schemas.clarification import QuestionCategory, QuestionOption, QuestionType

    options = None
    if question.options:
        options = [QuestionOption(**opt) for opt in question.options]

    return ClarificationQuestionResponse(
        id=question.id,
        question=question.question,
        question_type=QuestionType(question.question_type.value),
        category=QuestionCategory(question.category.value),
        options=options,
        help_text=question.help_text,
        scope_field=question.scope_field,
        answer=question.answer,
        answer_data=question.answer_data,
        is_required=question.is_required,
        is_answered=question.is_answered,
        order=question.order,
        created_at=question.created_at,
        answered_at=question.answered_at,
    )
