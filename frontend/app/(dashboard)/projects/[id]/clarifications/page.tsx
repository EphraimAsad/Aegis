'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  MessageCircle,
  Loader2,
  AlertCircle,
  CheckCircle,
  Send,
  RefreshCw,
  HelpCircle,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, ClarificationQuestion } from '@/types/api';

export default function ProjectClarificationsPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [questions, setQuestions] = useState<ClarificationQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [projectData, questionsData] = await Promise.all([
        apiClient.getProject(projectId),
        apiClient.getClarifications(projectId).catch(() => []),
      ]);
      setProject(projectData);
      setQuestions(questionsData);
    } catch (err) {
      setError('Failed to load clarifications');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerateQuestions = async () => {
    setGenerating(true);
    setError(null);
    try {
      const newQuestions = await apiClient.generateClarifications(projectId);
      setQuestions((prev) => [...prev, ...newQuestions]);
    } catch (err) {
      setError('Failed to generate questions');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmitAnswer = async (questionId: number) => {
    const answer = answers[questionId];
    if (!answer?.trim()) return;

    setSubmitting(questionId);
    setError(null);
    try {
      const updated = await apiClient.answerClarification(projectId, questionId, answer);
      setQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? updated : q))
      );
      setAnswers((prev) => {
        const newAnswers = { ...prev };
        delete newAnswers[questionId];
        return newAnswers;
      });
    } catch (err) {
      setError('Failed to submit answer');
      console.error(err);
    } finally {
      setSubmitting(null);
    }
  };

  const unansweredCount = questions.filter((q) => !q.is_answered).length;
  const answeredCount = questions.filter((q) => q.is_answered).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <Link
          href="/projects"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"
        >
          Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/projects/${projectId}`}
          className="p-2 hover:bg-muted rounded-md transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Research Clarifications</h1>
          <p className="text-muted-foreground">{project?.name}</p>
        </div>
        <button
          onClick={handleGenerateQuestions}
          disabled={generating}
          className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
        >
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Generate Questions
        </button>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border rounded-lg p-4 flex items-center gap-3">
          <div className="p-2 bg-yellow-100 rounded-full">
            <HelpCircle className="h-5 w-5 text-yellow-600" />
          </div>
          <div>
            <p className="text-2xl font-bold">{unansweredCount}</p>
            <p className="text-sm text-muted-foreground">Unanswered</p>
          </div>
        </div>
        <div className="border rounded-lg p-4 flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-full">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <p className="text-2xl font-bold">{answeredCount}</p>
            <p className="text-sm text-muted-foreground">Answered</p>
          </div>
        </div>
      </div>

      {/* Research Ready Status */}
      {unansweredCount === 0 && questions.length > 0 && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="h-5 w-5 text-green-600" />
          <div>
            <p className="font-medium text-green-800">Ready for Research</p>
            <p className="text-sm text-green-600">
              All clarification questions have been answered. You can now start the research job.
            </p>
          </div>
          <Link
            href={`/projects/${projectId}`}
            className="ml-auto px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            Go to Project
          </Link>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-md">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Questions List */}
      {questions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 border rounded-lg bg-muted/30">
          <MessageCircle className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-4">No clarification questions yet</p>
          <button
            onClick={handleGenerateQuestions}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Generate Questions
          </button>
          <p className="text-xs text-muted-foreground mt-2">
            AI will analyze your research objective and generate clarifying questions
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Unanswered Questions */}
          {questions.filter((q) => !q.is_answered).length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-yellow-600" />
                Unanswered Questions
              </h2>
              {questions
                .filter((q) => !q.is_answered)
                .map((question) => (
                  <div key={question.id} className="border rounded-lg p-4 space-y-3">
                    <p className="font-medium">{question.question}</p>
                    {question.context && (
                      <p className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                        {question.context}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <textarea
                        value={answers[question.id] || ''}
                        onChange={(e) =>
                          setAnswers((prev) => ({
                            ...prev,
                            [question.id]: e.target.value,
                          }))
                        }
                        placeholder="Type your answer..."
                        rows={2}
                        className="flex-1 px-3 py-2 border rounded-md bg-background resize-none"
                      />
                      <button
                        onClick={() => handleSubmitAnswer(question.id)}
                        disabled={
                          submitting === question.id ||
                          !answers[question.id]?.trim()
                        }
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 self-end"
                      >
                        {submitting === question.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* Answered Questions */}
          {questions.filter((q) => q.is_answered).length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Answered Questions
              </h2>
              {questions
                .filter((q) => q.is_answered)
                .map((question) => (
                  <div
                    key={question.id}
                    className="border border-green-200 bg-green-50/50 rounded-lg p-4 space-y-2"
                  >
                    <p className="font-medium">{question.question}</p>
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                      <p className="text-sm">{question.answer}</p>
                    </div>
                    {question.answered_at && (
                      <p className="text-xs text-muted-foreground">
                        Answered on{' '}
                        {new Date(question.answered_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
