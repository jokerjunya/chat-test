'use client'

import { useState, useEffect, useRef } from 'react'
import { ChatMessage } from '@/types/chat'
import { MessageBubble } from './MessageBubble'
import { SearchResults } from './SearchResults'

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [streamingMessage, setStreamingMessage] = useState('')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // WebSocket接続
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionStatus('connecting')
    
    const ws = new WebSocket('ws://localhost:8000/api/chat/stream')
    
    ws.onopen = () => {
      setConnectionStatus('connected')
      console.log('WebSocket接続成功')
    }
    
        ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // 新しいバックエンドフォーマットを処理
        if (data.type === 'message') {
          setIsLoading(false)
          setIsStreaming(false)
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.message,
            timestamp: new Date(),
            searchResults: data.search_results,
            thinking: data.thinking,
            hasThinking: data.has_thinking
          }])
          setStreamingMessage('')
        } else if (data.type === 'error') {
          setIsLoading(false)
          setIsStreaming(false)
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.message,
            timestamp: new Date(),
            isError: true
          }])
          setStreamingMessage('')
        } else {
          // 従来のフォーマット対応
          switch (data.type) {
            case 'status':
              setIsLoading(true)
              setStreamingMessage('')
              break
              
            case 'search_results':
              setSearchResults(data.content)
              break
              
            case 'token':
              setIsLoading(false)
              setIsStreaming(true)
              setStreamingMessage(prev => prev + data.content)
              break
              
            case 'completed':
              setIsLoading(false)
              setIsStreaming(false)
              setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: 'assistant',
                content: data.content,
                timestamp: new Date(),
                searchResults: data.search_results,
                thinking: data.thinking,
                hasThinking: data.has_thinking
              }])
              setStreamingMessage('')
              break
          }
        }
      } catch (error) {
        console.error('WebSocketメッセージの解析エラー:', error)
      }
    }
    
    ws.onclose = () => {
      setConnectionStatus('disconnected')
      console.log('WebSocket接続が閉じられました')
    }
    
    ws.onerror = (error) => {
      console.error('WebSocketエラー:', error)
      setConnectionStatus('disconnected')
    }
    
    wsRef.current = ws
  }

  // メッセージ送信
  const sendMessage = () => {
    if (!input.trim() || isLoading || isStreaming) return
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setSearchResults([])
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        messages: [...messages, userMessage].map(msg => ({
          role: msg.role,
          content: msg.content
        }))
      }))
    } else {
      connectWebSocket()
    }
  }

  // キーボードイベント
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // スクロール
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingMessage])

  useEffect(() => {
    connectWebSocket()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
      {/* ヘッダー */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">チャット</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            connectionStatus === 'connected' ? 'bg-green-500' : 
            connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
          }`}></div>
          <span className="text-sm text-gray-600">
            {connectionStatus === 'connected' ? '接続中' : 
             connectionStatus === 'connecting' ? '接続中...' : '切断中'}
          </span>
        </div>
      </div>

      {/* メッセージエリア */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <p>チャットを開始するには、下のメッセージ欄に質問を入力してください。</p>
            <p className="text-sm mt-2">Web検索結果を参考にした回答を生成します。</p>
          </div>
        )}
        
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {/* ストリーミング中のメッセージ */}
        {(isLoading || isStreaming) && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
              {isLoading && (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  <span className="text-sm text-gray-600">処理中...</span>
                </div>
              )}
              {isStreaming && (
                <div className="whitespace-pre-wrap text-gray-800">
                  {streamingMessage}
                  <span className="animate-pulse">|</span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* 検索結果 */}
        {searchResults.length > 0 && (
          <SearchResults results={searchResults} />
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 入力エリア */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="メッセージを入力..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading || isStreaming}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading || isStreaming}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading || isStreaming ? '送信中...' : '送信'}
          </button>
        </div>
      </div>
    </div>
  )
} 