'use client';

import { useState, useEffect, useRef } from 'react';
import { Network } from 'vis-network/standalone';
import { TrendingUp, Filter, Download } from 'lucide-react';

interface GraphNode {
  id: string;
  label: string;
  title: string;
  group: string;
  size: number;
  color: string;
}

interface GraphEdge {
  from: string;
  to: string;
  label: string;
  arrows: string;
  color: string;
  width: number;
}

interface GraphViewerProps {
  caseId: string;
  onNodeClick?: (nodeId: string) => void;
}

export default function GraphViewer({ caseId, onNodeClick }: GraphViewerProps) {
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    jurisdiction: 'all',
    treatment: 'all',
    timeRange: 'all'
  });
  
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstanceRef = useRef<Network | null>(null);

  useEffect(() => {
    if (caseId) {
      loadGraphData();
    }
  }, [caseId]);

  useEffect(() => {
    if (graphData && networkRef.current) {
      initializeNetwork();
    }
  }, [graphData]);

  const loadGraphData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`/api/v1/graphs/${caseId}/visualization`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load graph data');
      }

      const data = await response.json();
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const initializeNetwork = () => {
    if (!networkRef.current || !graphData) return;

    const options = {
      nodes: {
        shape: 'dot',
        font: {
          size: 14,
          face: 'Arial'
        },
        borderWidth: 2,
        shadow: true
      },
      edges: {
        width: 2,
        shadow: true,
        font: {
          size: 12,
          align: 'middle'
        },
        smooth: {
          type: 'continuous'
        }
      },
      physics: {
        stabilization: false,
        barnesHut: {
          gravitationalConstant: -80000,
          springConstant: 0.001,
          springLength: 200
        }
      },
      interaction: {
        navigationButtons: true,
        keyboard: true
      }
    };

    const network = new Network(networkRef.current, graphData, options);
    
    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        onNodeClick?.(nodeId);
      }
    });

    networkInstanceRef.current = network;
  };

  const applyFilters = () => {
    // Apply filters to graph data
    // This would filter nodes and edges based on selected criteria
    console.log('Applying filters:', filters);
  };

  const exportGraph = () => {
    if (networkInstanceRef.current) {
      const canvas = networkInstanceRef.current.canvas.frame.canvas;
      const link = document.createElement('a');
      link.download = `precedent-graph-${caseId}.png`;
      link.href = canvas.toDataURL();
      link.click();
    }
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <TrendingUp className="h-12 w-12 mx-auto mb-2" />
            <h3 className="text-lg font-semibold">Error Loading Graph</h3>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadGraphData}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <TrendingUp className="h-6 w-6 text-blue-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">
              Precedent Graph
            </h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={exportGraph}
              className="flex items-center space-x-1 text-gray-600 hover:text-gray-800 p-2 rounded"
              title="Export graph"
            >
              <Download className="h-4 w-4" />
              <span className="text-sm">Export</span>
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="mt-4 flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-600">Filters:</span>
          </div>
          
          <select
            value={filters.jurisdiction}
            onChange={(e) => setFilters(prev => ({ ...prev, jurisdiction: e.target.value }))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="all">All Jurisdictions</option>
            <option value="federal">Federal</option>
            <option value="state">State</option>
          </select>

          <select
            value={filters.treatment}
            onChange={(e) => setFilters(prev => ({ ...prev, treatment: e.target.value }))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="all">All Treatments</option>
            <option value="followed">Followed</option>
            <option value="overruled">Overruled</option>
            <option value="distinguished">Distinguished</option>
          </select>

          <button
            onClick={applyFilters}
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Graph Container */}
      <div className="relative">
        {isLoading ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-gray-600">Loading precedent graph...</p>
            </div>
          </div>
        ) : (
          <div 
            ref={networkRef} 
            className="h-96 w-full"
            style={{ minHeight: '400px' }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="p-4 border-t bg-gray-50">
        <div className="flex items-center justify-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span>Current Case</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>Cited Cases</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span>Overruled</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span>Distinguished</span>
          </div>
        </div>
      </div>
    </div>
  );
}
