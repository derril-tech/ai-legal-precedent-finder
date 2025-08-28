'use client';

import { useState } from 'react';
import { Search, BookOpen, FileText, Users, TrendingUp } from 'lucide-react';

export default function HomePage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    // TODO: Implement search functionality
    console.log('Searching for:', query);
    setIsSearching(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <BookOpen className="h-8 w-8 text-blue-600" />
              <h1 className="ml-3 text-2xl font-bold text-gray-900">
                AI Legal Precedent Finder
              </h1>
            </div>
            <nav className="flex space-x-8">
              <a href="#" className="text-gray-500 hover:text-gray-900">
                Search
              </a>
              <a href="#" className="text-gray-500 hover:text-gray-900">
                Cases
              </a>
              <a href="#" className="text-gray-500 hover:text-gray-900">
                Graphs
              </a>
              <a href="#" className="text-gray-500 hover:text-gray-900">
                Exports
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Find Legal Precedents with AI
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Ask legal questions and instantly see precedent-backed answers with 
            citations, case passages, and dynamic precedent graphs.
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
            <div className="flex shadow-lg rounded-lg overflow-hidden">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a legal question... (e.g., 'What is the standard for proving negligence?')"
                className="flex-1 px-6 py-4 text-lg border-0 focus:ring-0 focus:outline-none"
                disabled={isSearching}
              />
              <button
                type="submit"
                disabled={isSearching || !query.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 px-8 py-4 text-white font-semibold transition-colors"
              >
                {isSearching ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Searching...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <Search className="h-5 w-5 mr-2" />
                    Search
                  </div>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center mb-4">
              <Search className="h-8 w-8 text-blue-600" />
              <h3 className="ml-3 text-lg font-semibold text-gray-900">
                Smart Search
              </h3>
            </div>
            <p className="text-gray-600">
              Hybrid semantic and keyword search across millions of legal cases.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center mb-4">
              <FileText className="h-8 w-8 text-green-600" />
              <h3 className="ml-3 text-lg font-semibold text-gray-900">
                Auto-Citations
              </h3>
            </div>
            <p className="text-gray-600">
              Get answers with inline citations to relevant cases and passages.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center mb-4">
              <TrendingUp className="h-8 w-8 text-purple-600" />
              <h3 className="ml-3 text-lg font-semibold text-gray-900">
                Precedent Graphs
              </h3>
            </div>
            <p className="text-gray-600">
              Visualize how cases relate to each other with interactive graphs.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center mb-4">
              <Users className="h-8 w-8 text-orange-600" />
              <h3 className="ml-3 text-lg font-semibold text-gray-900">
                Expert Summaries
              </h3>
            </div>
            <p className="text-gray-600">
              AI-generated summaries of holdings, reasoning, and key dicta.
            </p>
          </div>
        </div>

        {/* Recent Searches */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Searches
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">
                "What constitutes reasonable doubt in criminal cases?"
              </span>
              <span className="text-sm text-gray-500">2 hours ago</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">
                "Standards for proving medical malpractice"
              </span>
              <span className="text-sm text-gray-500">1 day ago</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">
                "Fourth Amendment search and seizure requirements"
              </span>
              <span className="text-sm text-gray-500">3 days ago</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <p className="text-gray-400">
              © 2024 AI Legal Precedent Finder. Not legal advice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
