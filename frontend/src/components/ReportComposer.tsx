'use client';

import { useState } from 'react';
import { FileText, Download, FileSpreadsheet, Code, Loader } from 'lucide-react';

interface ReportComposerProps {
  sessionId: string;
  onClose: () => void;
}

interface ExportResult {
  export_id: string;
  status: string;
  export_type: string;
  file_format: string;
  signed_url: string;
  citations_count: number;
}

export default function ReportComposer({ sessionId, onClose }: ReportComposerProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedExports, setGeneratedExports] = useState<ExportResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const generateExport = async (exportType: string) => {
    try {
      setIsGenerating(true);
      setError(null);

      const response = await fetch(`/api/v1/exports/${exportType}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate ${exportType} export`);
      }

      const result: ExportResult = await response.json();
      
      if (result.status === 'success') {
        setGeneratedExports(prev => [...prev, result]);
      } else {
        throw new Error(result.error || `Failed to generate ${exportType} export`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadExport = (exportResult: ExportResult) => {
    const link = document.createElement('a');
    link.href = exportResult.signed_url;
    link.download = `${exportResult.export_type}-${sessionId}.${exportResult.file_format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getExportIcon = (exportType: string) => {
    switch (exportType) {
      case 'brief':
        return <FileText className="h-5 w-5" />;
      case 'citations':
        return <FileSpreadsheet className="h-5 w-5" />;
      case 'json':
        return <Code className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getExportTitle = (exportType: string) => {
    switch (exportType) {
      case 'brief':
        return 'Legal Brief';
      case 'citations':
        return 'Citation Table';
      case 'json':
        return 'JSON Bundle';
      default:
        return exportType;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <FileText className="h-6 w-6 text-blue-600 mr-2" />
          <h2 className="text-xl font-semibold text-gray-900">
            Generate Reports
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 p-2"
        >
          ×
        </button>
      </div>

      {/* Export Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button
          onClick={() => generateExport('brief')}
          disabled={isGenerating}
          className="flex flex-col items-center p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50"
        >
          <FileText className="h-8 w-8 text-blue-600 mb-2" />
          <span className="font-medium text-gray-900">Legal Brief</span>
          <span className="text-sm text-gray-600">DOCX format</span>
        </button>

        <button
          onClick={() => generateExport('citations')}
          disabled={isGenerating}
          className="flex flex-col items-center p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50"
        >
          <FileSpreadsheet className="h-8 w-8 text-green-600 mb-2" />
          <span className="font-medium text-gray-900">Citation Table</span>
          <span className="text-sm text-gray-600">CSV format</span>
        </button>

        <button
          onClick={() => generateExport('json')}
          disabled={isGenerating}
          className="flex flex-col items-center p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50"
        >
          <Code className="h-8 w-8 text-purple-600 mb-2" />
          <span className="font-medium text-gray-900">JSON Bundle</span>
          <span className="text-sm text-gray-600">Complete data</span>
        </button>
      </div>

      {/* Loading State */}
      {isGenerating && (
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <Loader className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
            <p className="text-gray-600">Generating export...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 underline mt-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Generated Exports */}
      {generatedExports.length > 0 && (
        <div className="border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Generated Reports
          </h3>
          <div className="space-y-3">
            {generatedExports.map((exportResult) => (
              <div
                key={exportResult.export_id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {getExportIcon(exportResult.export_type)}
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {getExportTitle(exportResult.export_type)}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {exportResult.citations_count} citations • {exportResult.file_format.toUpperCase()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => downloadExport(exportResult)}
                  className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 p-2 rounded"
                >
                  <Download className="h-4 w-4" />
                  <span className="text-sm">Download</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          <strong>Disclaimer:</strong> All exports are generated for research purposes only 
          and do not constitute legal advice. Please consult with a qualified attorney 
          for specific legal guidance.
        </p>
      </div>
    </div>
  );
}
