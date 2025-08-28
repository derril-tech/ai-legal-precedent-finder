'use client';

import { useState, useEffect } from 'react';
import { FileText, ExternalLink, Copy, Check } from 'lucide-react';

interface Citation {
  id: string;
  case_id: string;
  case_name: string;
  citation_text: string;
  passage_content: string;
  relevance_score: number;
}

interface AnswerPanelProps {
  sessionId: string;
  question: string;
  onClose: () => void;
}

export default function AnswerPanel({ sessionId, question, onClose }: AnswerPanelProps) {
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (sessionId) {
      streamAnswer();
    }
  }, [sessionId]);

  const streamAnswer = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/v1/qa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          question,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get answer');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      let accumulatedAnswer = '';
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setIsLoading(false);
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'answer_chunk') {
                accumulatedAnswer += parsed.content;
                setAnswer(accumulatedAnswer);
              } else if (parsed.type === 'citation') {
                setCitations(prev => [...prev, parsed.citation]);
              }
            } catch (e) {
              // Ignore parsing errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setIsLoading(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatAnswerWithCitations = (text: string) => {
    // Simple citation formatting - in a real implementation, this would be more sophisticated
    return text.split('\n').map((line, index) => (
      <p key={index} className="mb-4 leading-relaxed">
        {line}
      </p>
    ));
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Answer</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>
        <div className="text-red-600 bg-red-50 p-4 rounded-lg">
          <p>Error: {error}</p>
          <button
            onClick={streamAnswer}
            className="mt-2 text-blue-600 hover:text-blue-800 underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Answer</h2>
          <p className="text-sm text-gray-500 mt-1">Question: {question}</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={copyToClipboard}
            className="flex items-center space-x-1 text-gray-600 hover:text-gray-800 p-2 rounded"
            title="Copy answer"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4" />
                <span className="text-sm">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span className="text-sm">Copy</span>
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-2"
          >
            ×
          </button>
        </div>
      </div>

      {/* Answer Content */}
      <div className="mb-6">
        {isLoading ? (
          <div className="space-y-4">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
            <div className="flex items-center text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              Generating answer...
            </div>
          </div>
        ) : (
          <div className="prose max-w-none">
            {formatAnswerWithCitations(answer)}
          </div>
        )}
      </div>

      {/* Citations */}
      {citations.length > 0 && (
        <div className="border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <FileText className="h-5 w-5 mr-2" />
            Citations ({citations.length})
          </h3>
          <div className="space-y-4">
            {citations.map((citation, index) => (
              <div
                key={citation.id}
                className="bg-gray-50 rounded-lg p-4 border-l-4 border-blue-500"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {citation.case_name}
                    </h4>
                    <p className="text-sm text-gray-600 font-mono">
                      {citation.citation_text}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {Math.round(citation.relevance_score * 100)}% relevant
                    </span>
                    <button
                      className="text-blue-600 hover:text-blue-800"
                      title="View case"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {citation.passage_content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          <strong>Disclaimer:</strong> This answer is based on legal precedent analysis 
          and is provided for research purposes only. It does not constitute legal advice. 
          Please consult with a qualified attorney for specific legal guidance.
        </p>
      </div>
    </div>
  );
}
