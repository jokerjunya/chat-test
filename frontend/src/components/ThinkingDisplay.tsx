import React, { useState } from 'react';
// CSS用のミニマルなアイコン（Heroicons不要）

interface ThinkingDisplayProps {
  thinking: string;
  isExpanded?: boolean;
}

const ThinkingDisplay: React.FC<ThinkingDisplayProps> = ({ 
  thinking, 
  isExpanded = false 
}) => {
  const [isOpen, setIsOpen] = useState(isExpanded);

  if (!thinking) return null;

  return (
    <div className="mb-4 border rounded-lg bg-gray-50 border-gray-200">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between text-left text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
      >
        <span className="flex items-center">
          <span className="text-gray-500 mr-2">🤔</span>
          思考プロセス
        </span>
        <span className="text-gray-400">
          {isOpen ? '▲' : '▼'}
        </span>
      </button>
      
      {isOpen && (
        <div className="border-t border-gray-200">
          <div className="px-4 py-3 bg-white">
            <div className="text-sm text-gray-600 whitespace-pre-wrap">
              {thinking}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ThinkingDisplay; 