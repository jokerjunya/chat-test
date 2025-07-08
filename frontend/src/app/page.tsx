'use client'

import { useState, useEffect, useRef } from 'react'
import { ChatInterface } from '@/components/ChatInterface'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <header className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              ゼロコスト日本語チャットアプリ
            </h1>
            <p className="text-gray-600">
              ローカルLLM + Web検索で無料チャット体験
            </p>
          </header>
          
          <ChatInterface />
        </div>
      </div>
    </main>
  )
}
