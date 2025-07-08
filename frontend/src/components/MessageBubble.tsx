'use client'

import { ChatMessage } from '@/types/chat'
import ThinkingDisplay from './ThinkingDisplay'

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-lg p-3 ${
        isUser 
          ? 'bg-blue-500 text-white' 
          : message.isError 
          ? 'bg-red-100 text-red-800 border border-red-300'
          : 'bg-gray-100 text-gray-800'
      }`}>
        {/* 思考表示（アシスタントのメッセージでかつ思考がある場合のみ） */}
        {!isUser && message.hasThinking && message.thinking && (
          <ThinkingDisplay thinking={message.thinking} />
        )}
        
        <div className="whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <div className={`text-xs mt-1 ${
          isUser ? 'text-blue-100' : 'text-gray-500'
        }`}>
          {message.timestamp.toLocaleTimeString('ja-JP', { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  )
} 