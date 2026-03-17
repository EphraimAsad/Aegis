"""Clarification service for question generation and management."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ProviderError
from app.models.clarification import (
    ClarificationQuestion,
    QuestionCategory,
    QuestionType,
)
from app.models.project import Project, ProjectStatus
from app.providers import Message, MessageRole, ChatSettings, get_provider_manager
from app.schemas.clarification import AnswerQuestionRequest


# Prompt template for generating clarification questions
CLARIFICATION_PROMPT = '''You are an expert research assistant helping to clarify a research project's scope.

The user has provided the following research objective:
"{research_objective}"

Project name: {project_name}
{description_section}

Your task is to generate clarification questions that will help refine the research scope.
Focus on questions that will help determine:
1. Specific disciplines or fields to search
2. Key terminology and synonyms
3. Time period of interest
4. Types of documents (journals, conferences, preprints)
5. Any specific authors, journals, or institutions to focus on
6. Geographic or language constraints
7. What the expected output should be

Generate 3-5 focused questions. For each question, provide:
- The question text
- The type: "text", "single_select", "multi_select", "date_range", "number", or "boolean"
- Category: "scope", "methodology", "sources", "constraints", or "output"
- For select types, provide options
- A brief help text explaining why this matters
- Which scope field it maps to (if any): "disciplines", "keywords", "excluded_keywords", "date_range_start", "date_range_end", "languages", "document_types", "min_citations", "include_preprints", "geographic_focus", "specific_journals", "specific_authors"

Respond in JSON format:
{{
  "questions": [
    {{
      "question": "What specific academic disciplines should this research focus on?",
      "question_type": "multi_select",
      "category": "scope",
      "options": [
        {{"value": "computer_science", "label": "Computer Science"}},
        {{"value": "biology", "label": "Biology"}}
      ],
      "help_text": "Selecting specific disciplines helps narrow the search to relevant fields.",
      "scope_field": "disciplines",
      "is_required": true
    }}
  ]
}}'''


class ClarificationService:
    """Service for clarification question operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def get_questions(self, project_id: int) -> list[ClarificationQuestion]:
        """
        Get all clarification questions for a project.

        Args:
            project_id: The project ID

        Returns:
            List of clarification questions
        """
        result = await self.db.execute(
            select(ClarificationQuestion)
            .where(ClarificationQuestion.project_id == project_id)
            .order_by(ClarificationQuestion.order)
        )
        return list(result.scalars().all())

    async def get_question(self, question_id: int) -> ClarificationQuestion:
        """
        Get a specific clarification question.

        Args:
            question_id: The question ID

        Returns:
            The clarification question

        Raises:
            NotFoundError: If question not found
        """
        result = await self.db.execute(
            select(ClarificationQuestion).where(ClarificationQuestion.id == question_id)
        )
        question = result.scalar_one_or_none()

        if not question:
            raise NotFoundError(
                f"Clarification question with id {question_id} not found",
                details={"question_id": question_id},
            )

        return question

    async def generate_questions(
        self,
        project: Project,
        force_regenerate: bool = False,
    ) -> list[ClarificationQuestion]:
        """
        Generate clarification questions for a project using AI.

        Args:
            project: The project to generate questions for
            force_regenerate: Whether to regenerate even if questions exist

        Returns:
            List of generated questions
        """
        # Check if questions already exist
        existing = await self.get_questions(project.id)
        if existing and not force_regenerate:
            return existing

        # Delete existing questions if regenerating
        if existing and force_regenerate:
            for q in existing:
                await self.db.delete(q)
            await self.db.flush()

        # Build the prompt
        description_section = ""
        if project.description:
            description_section = f"Description: {project.description}"

        prompt = CLARIFICATION_PROMPT.format(
            research_objective=project.research_objective,
            project_name=project.name,
            description_section=description_section,
        )

        # Get provider and generate questions
        manager = get_provider_manager()
        provider = manager.get(project.provider)

        try:
            messages = [
                Message(role=MessageRole.SYSTEM, content="You are a helpful research assistant. Always respond with valid JSON."),
                Message(role=MessageRole.USER, content=prompt),
            ]

            settings = ChatSettings(temperature=0.7, json_mode=provider.supports_json_mode())
            response = await provider.chat(messages, project.model, settings)

            # Parse the response
            questions_data = json.loads(response.content)
            questions = []

            for i, q_data in enumerate(questions_data.get("questions", [])):
                question = ClarificationQuestion(
                    project_id=project.id,
                    question=q_data["question"],
                    question_type=QuestionType(q_data.get("question_type", "text")),
                    category=QuestionCategory(q_data.get("category", "scope")),
                    options=q_data.get("options"),
                    help_text=q_data.get("help_text"),
                    scope_field=q_data.get("scope_field"),
                    is_required=q_data.get("is_required", True),
                    order=i,
                )
                self.db.add(question)
                questions.append(question)

            await self.db.flush()

            # Refresh all questions
            for q in questions:
                await self.db.refresh(q)

            return questions

        except json.JSONDecodeError as e:
            raise ProviderError(
                "Failed to parse AI response as JSON",
                details={"error": str(e)},
            )
        except Exception as e:
            raise ProviderError(
                f"Failed to generate clarification questions: {str(e)}",
                details={"error": str(e)},
            )

    async def answer_question(
        self,
        question_id: int,
        request: AnswerQuestionRequest,
    ) -> ClarificationQuestion:
        """
        Answer a clarification question.

        Args:
            question_id: The question ID
            request: The answer request

        Returns:
            The updated question
        """
        question = await self.get_question(question_id)

        question.answer = request.answer
        question.answer_data = request.answer_data
        question.answered_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(question)

        # Update project scope if this question maps to a scope field
        if question.scope_field:
            await self._update_scope_from_answer(question)

        return question

    async def _update_scope_from_answer(self, question: ClarificationQuestion) -> None:
        """Update project scope based on a question answer."""
        if not question.scope_field:
            return

        # Get the project
        result = await self.db.execute(
            select(Project).where(Project.id == question.project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return

        scope = project.scope or {}

        # Update the appropriate scope field
        if question.answer_data:
            # Use structured answer data
            scope[question.scope_field] = question.answer_data.get("value", question.answer_data)
        elif question.answer:
            # Use text answer - try to parse as list if applicable
            if question.question_type in [QuestionType.MULTI_SELECT]:
                try:
                    scope[question.scope_field] = json.loads(question.answer)
                except json.JSONDecodeError:
                    scope[question.scope_field] = [question.answer]
            elif question.question_type == QuestionType.BOOLEAN:
                scope[question.scope_field] = question.answer.lower() in ["yes", "true", "1"]
            elif question.question_type == QuestionType.NUMBER:
                try:
                    scope[question.scope_field] = int(question.answer)
                except ValueError:
                    scope[question.scope_field] = question.answer
            else:
                scope[question.scope_field] = question.answer

        project.scope = scope
        await self.db.flush()

    async def get_status(self, project_id: int) -> dict:
        """
        Get clarification status for a project.

        Args:
            project_id: The project ID

        Returns:
            Status information
        """
        questions = await self.get_questions(project_id)

        total = len(questions)
        answered = sum(1 for q in questions if q.is_answered)
        required_answered = sum(1 for q in questions if q.is_required and q.is_answered)
        required_total = sum(1 for q in questions if q.is_required)

        return {
            "project_id": project_id,
            "total_questions": total,
            "answered_questions": answered,
            "is_complete": answered == total,
            "can_proceed": required_answered == required_total,
        }
