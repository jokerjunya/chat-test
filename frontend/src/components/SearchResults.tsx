'use client'

import { SearchResult } from '@/types/chat'

interface SearchResultsProps {
  results: SearchResult[]
}

export function SearchResults({ results }: SearchResultsProps) {
  if (!results || results.length === 0) {
    return null
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <h3 className="text-sm font-semibold text-blue-800 mb-2 flex items-center">
        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
        </svg>
        検索結果を参考にしています
      </h3>
      <div className="space-y-2">
        {results.slice(0, 3).map((result, index) => (
          <div key={index} className="bg-white rounded p-3 border border-blue-100">
            <h4 className="font-medium text-blue-900 text-sm mb-1">
              {result.title}
            </h4>
            {result.url && (
              <a 
                href={result.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 underline mb-1 block"
              >
                {result.url}
              </a>
            )}
            <p className="text-xs text-gray-600 line-clamp-2">
              {result.snippet}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
} 