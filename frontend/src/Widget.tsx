/**
 * SunsetBot Chat Widget
 *
 * A self-contained chat interface that connects to the SunsetBot WebSocket API.
 * Renders inside a shadow DOM for CSS isolation from the host page.
 *
 * Features:
 * - Floating chat bubble that opens a chat panel
 * - Auto-connects WebSocket with JWT auth
 * - Message bubbles with typing indicator
 * - Product cards with images and prices
 * - Mobile responsive
 * - Customizable primary color
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'

// ============================================================================
// TYPES
// ============================================================================

interface Product {
  id: string
  title: string
  price: number
  image_url?: string
  url?: string
  inventory: number
}

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  text: string
  products?: Product[]
  timestamp: Date
}

interface WidgetProps {
  shop: string
  server: string
  primaryColor: string
  position: 'bottom-right' | 'bottom-left'
}

interface TokenResponse {
  token: string
  session_id: string
  store_id: string
  store_name: string
  widget_color: string
  welcome_message: string | null
}

// ============================================================================
// WIDGET COMPONENT
// ============================================================================

export function Widget({ shop, server, primaryColor, position }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState('')

  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const tokenDataRef = useRef<TokenResponse | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  // ─────────────── WebSocket Connection ───────────────

  const connect = useCallback(async () => {
    // Step 1: Get JWT token from server
    if (!tokenDataRef.current) {
      try {
        const tokenUrl = shop
          ? `${server}/shopify/widget-token?shop=${encodeURIComponent(shop)}`
          : `${server}/shopify/widget-token?shop=demo-store.myshopify.com`

        const resp = await fetch(tokenUrl)

        if (!resp.ok) {
          // In dev mode without Shopify, connect directly without token
          tokenDataRef.current = {
            token: '',
            session_id: `local-${Date.now().toString(36)}`,
            store_id: 'demo-store',
            store_name: 'Demo Store',
            widget_color: primaryColor,
            welcome_message: null,
          }
        } else {
          tokenDataRef.current = await resp.json()
        }
      } catch {
        // Fallback for local development
        tokenDataRef.current = {
          token: '',
          session_id: `local-${Date.now().toString(36)}`,
          store_id: 'demo-store',
          store_name: 'Demo Store',
          widget_color: primaryColor,
          welcome_message: null,
        }
      }
    }

    const tokenData = tokenDataRef.current!
    const { token, session_id, store_id } = tokenData

    // Step 2: Connect WebSocket
    const protocol = server.startsWith('https') ? 'wss' : 'ws'
    const host = server.replace(/^https?:\/\//, '')
    const tokenParam = token ? `?token=${token}` : ''
    const wsUrl = `${protocol}://${host}/ws/chat/${store_id}/${session_id}${tokenParam}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setConnectionError('')
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'typing') {
            setIsTyping(true)
            return
          }

          if (data.type === 'error') {
            setIsTyping(false)
            addMessage('system', data.error || 'Something went wrong')
            return
          }

          if (data.type === 'message') {
            setIsTyping(false)
            addMessage('assistant', data.text, data.products)
          }
        } catch {
          console.error('SunsetBot: Failed to parse message')
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        wsRef.current = null

        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          reconnectAttempts.current++
          setTimeout(connect, delay)
        }
      }

      ws.onerror = () => {
        setConnectionError('Unable to connect. Retrying...')
      }
    } catch (err) {
      setConnectionError('Connection failed')
    }
  }, [server, shop, primaryColor])

  // Connect when widget opens
  useEffect(() => {
    if (isOpen && !wsRef.current) {
      connect()
    }

    return () => {
      // Don't close on unmount — keep connection alive while widget exists
    }
  }, [isOpen, connect])

  // ─────────────── Message Handling ───────────────

  const addMessage = (type: ChatMessage['type'], text: string, products?: Product[]) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        type,
        text,
        products: products?.length ? products : undefined,
        timestamp: new Date(),
      },
    ])
  }

  const sendMessage = () => {
    const text = input.trim()
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    addMessage('user', text)
    wsRef.current.send(JSON.stringify({ message: text }))
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ─────────────── Render ───────────────

  const posStyle = position === 'bottom-left'
    ? { left: '20px', right: 'auto' }
    : { right: '20px', left: 'auto' }

  return (
    <>
      <style>{getStyles(primaryColor)}</style>

      {/* Chat Panel */}
      {isOpen && (
        <div className="sb-panel" style={posStyle}>
          {/* Header */}
          <div className="sb-header">
            <div className="sb-header-info">
              <div className="sb-header-dot" />
              <span className="sb-header-title">Shopping Assistant</span>
            </div>
            <button className="sb-close-btn" onClick={() => setIsOpen(false)} aria-label="Close chat">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="sb-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`sb-msg sb-msg-${msg.type}`}>
                <div className="sb-msg-bubble">{msg.text}</div>
                {msg.products && msg.products.length > 0 && (
                  <div className="sb-products">
                    {msg.products.map((product) => (
                      <div key={product.id} className="sb-product-card">
                        {product.image_url && (
                          <img
                            src={product.image_url}
                            alt={product.title}
                            className="sb-product-img"
                            loading="lazy"
                          />
                        )}
                        <div className="sb-product-info">
                          <div className="sb-product-title">{product.title}</div>
                          <div className="sb-product-price">${product.price.toFixed(2)}</div>
                          {product.inventory < 10 && product.inventory > 0 && (
                            <div className="sb-product-stock">Only {product.inventory} left!</div>
                          )}
                        </div>
                        {product.url && (
                          <a
                            href={product.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="sb-product-link"
                          >
                            View
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="sb-msg sb-msg-assistant">
                <div className="sb-msg-bubble sb-typing">
                  <span className="sb-dot" />
                  <span className="sb-dot" />
                  <span className="sb-dot" />
                </div>
              </div>
            )}

            {connectionError && (
              <div className="sb-msg sb-msg-system">
                <div className="sb-msg-bubble">{connectionError}</div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="sb-input-area">
            <input
              ref={inputRef}
              type="text"
              className="sb-input"
              placeholder="Ask me anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isConnected}
              maxLength={2000}
            />
            <button
              className="sb-send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || !isConnected}
              aria-label="Send message"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Floating Bubble */}
      <button
        className="sb-bubble"
        style={posStyle}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M18 6L6 18M6 6L18 18" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </button>
    </>
  )
}

// ============================================================================
// STYLES — Injected into shadow DOM
// ============================================================================

function getStyles(primaryColor: string): string {
  return `
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }

    /* ─── Floating Bubble ─── */
    .sb-bubble {
      position: fixed;
      bottom: 20px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${primaryColor};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      z-index: 2147483646;
    }
    .sb-bubble:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }

    /* ─── Chat Panel ─── */
    .sb-panel {
      position: fixed;
      bottom: 90px;
      width: 380px;
      max-width: calc(100vw - 40px);
      height: 520px;
      max-height: calc(100vh - 120px);
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 2147483646;
      animation: sb-slide-up 0.25s ease-out;
    }

    @keyframes sb-slide-up {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* ─── Header ─── */
    .sb-header {
      background: ${primaryColor};
      color: white;
      padding: 16px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .sb-header-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .sb-header-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #4ade80;
    }
    .sb-header-title {
      font-size: 15px;
      font-weight: 600;
    }
    .sb-close-btn {
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      padding: 4px;
      opacity: 0.8;
      transition: opacity 0.15s;
    }
    .sb-close-btn:hover { opacity: 1; }

    /* ─── Messages Area ─── */
    .sb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f8f9fa;
    }
    .sb-messages::-webkit-scrollbar { width: 4px; }
    .sb-messages::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }

    /* ─── Message Bubbles ─── */
    .sb-msg { display: flex; flex-direction: column; }
    .sb-msg-user { align-items: flex-end; }
    .sb-msg-assistant { align-items: flex-start; }
    .sb-msg-system { align-items: center; }

    .sb-msg-bubble {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.45;
      word-wrap: break-word;
      white-space: pre-wrap;
    }
    .sb-msg-user .sb-msg-bubble {
      background: ${primaryColor};
      color: white;
      border-bottom-right-radius: 4px;
    }
    .sb-msg-assistant .sb-msg-bubble {
      background: white;
      color: #1a1a2e;
      border: 1px solid #e5e7eb;
      border-bottom-left-radius: 4px;
    }
    .sb-msg-system .sb-msg-bubble {
      background: #fef3c7;
      color: #92400e;
      font-size: 12px;
      border-radius: 8px;
    }

    /* ─── Typing Indicator ─── */
    .sb-typing {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
    }
    .sb-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #9ca3af;
      animation: sb-bounce 1.4s infinite ease-in-out;
    }
    .sb-dot:nth-child(2) { animation-delay: 0.2s; }
    .sb-dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes sb-bounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* ─── Product Cards ─── */
    .sb-products {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 8px;
      max-width: 85%;
    }
    .sb-product-card {
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      transition: box-shadow 0.15s;
    }
    .sb-product-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    .sb-product-img {
      width: 56px;
      height: 56px;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
      background: #f3f4f6;
    }
    .sb-product-info {
      flex: 1;
      min-width: 0;
    }
    .sb-product-title {
      font-size: 13px;
      font-weight: 600;
      color: #1a1a2e;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sb-product-price {
      font-size: 14px;
      font-weight: 700;
      color: ${primaryColor};
      margin-top: 2px;
    }
    .sb-product-stock {
      font-size: 11px;
      color: #ef4444;
      margin-top: 2px;
    }
    .sb-product-link {
      font-size: 12px;
      color: ${primaryColor};
      text-decoration: none;
      font-weight: 600;
      padding: 4px 10px;
      border: 1px solid ${primaryColor};
      border-radius: 6px;
      flex-shrink: 0;
      transition: background 0.15s, color 0.15s;
    }
    .sb-product-link:hover {
      background: ${primaryColor};
      color: white;
    }

    /* ─── Input Area ─── */
    .sb-input-area {
      padding: 12px;
      display: flex;
      gap: 8px;
      border-top: 1px solid #e5e7eb;
      background: white;
      flex-shrink: 0;
    }
    .sb-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #e5e7eb;
      border-radius: 24px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.15s;
      background: #f8f9fa;
    }
    .sb-input:focus {
      border-color: ${primaryColor};
      background: white;
    }
    .sb-input::placeholder {
      color: #9ca3af;
    }
    .sb-input:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .sb-send-btn {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: ${primaryColor};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      flex-shrink: 0;
      transition: opacity 0.15s, transform 0.1s;
    }
    .sb-send-btn:hover:not(:disabled) {
      opacity: 0.9;
      transform: scale(1.05);
    }
    .sb-send-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* ─── Mobile Responsive ─── */
    @media (max-width: 440px) {
      .sb-panel {
        width: calc(100vw - 16px);
        height: calc(100vh - 100px);
        bottom: 80px;
        left: 8px !important;
        right: 8px !important;
        border-radius: 12px;
      }
      .sb-bubble {
        width: 52px;
        height: 52px;
      }
    }
  `
}
