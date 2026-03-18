"""Clarification question schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QuestionType(StrEnum):
    """Types of clarification questions."""

    TEXT = "text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    DATE_RANGE = "date_range"
    NUMBER = "number"
    BOOLEAN = "boolean"


class QuestionCategory(StrEnum):
    """Categories of clarification questions."""

    SCOPE = "scope"
    METHODOLOGY = "methodology"
    SOURCES = "sources"
    CONSTRAINTS = "constraints"
    OUTPUT = "output"
    OTHER = "other"


class QuestionOption(BaseModel):
    """Option for select-type questions."""

    value: str
    label: str


# Request schemas


class AnswerQuestionRequest(BaseModel):
    """Request to answer a clarification question."""

    answer: str | None = Field(None, description="Text answer")
    answer_data: dict | None = Field(None, description="Structured answer data")


class GenerateQuestionsRequest(BaseModel):
    """Request to generate clarification questions."""

    force_regenerate: bool = Field(
        False, description="Regenerate even if questions exist"
    )


# Response schemas


class ClarificationQuestionResponse(BaseModel):
    """Clarification question response."""

    id: int
    question: str
    question_type: QuestionType
    category: QuestionCategory
    options: list[QuestionOption] | None = None
    help_text: str | None = None
    scope_field: str | None = None
    answer: str | None = None
    answer_data: dict | None = None
    is_required: bool
    is_answered: bool
    order: int
    created_at: datetime
    answered_at: datetime | None = None

    class Config:
        from_attributes = True


class ClarificationQuestionsListResponse(BaseModel):
    """Response for listing clarification questions."""

    project_id: int
    questions: list[ClarificationQuestionResponse]
    total: int
    answered: int
    unanswered: int


class ClarificationStatusResponse(BaseModel):
    """Status of clarification process."""

    project_id: int
    total_questions: int
    answered_questions: int
    is_complete: bool
    can_proceed: bool
