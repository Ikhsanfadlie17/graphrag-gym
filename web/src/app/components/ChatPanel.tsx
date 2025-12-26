'use client';

import { useState, FormEvent, KeyboardEvent } from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatPanelProps {
  onQuerySubmit: (query: string, cypher: string) => void;
  onEvaluateQuery?: (
    question: string,
    answer: string,
    responseTimeMs: number
  ) => void;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  question?: string;
  responseTimeMs?: number;
}

export default function ChatPanel({
  onQuerySubmit,
  onEvaluateQuery,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content:
        'Halo! Saya Graph RAG Exercise Assistant. Tanyakan tentang latihan, anatomi otot, peralatan, atau konsep ilmiah training.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // quick prompts hanya tampil sebelum user mengirim pertanyaan pertama
  const [showQuickPrompts, setShowQuickPrompts] = useState(true);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // setelah user mulai pakai sistem, sembunyikan quick prompts
    if (showQuickPrompts) {
      setShowQuickPrompts(false);
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentQuestion = input.trim();
    setInput('');
    setIsLoading(true);

    const startTime = performance.now();

    try {
      const response = await fetch('http://localhost:5000/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: currentQuestion }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const endTime = performance.now();
      const responseTimeMs = endTime - startTime;

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.answer,
        timestamp: new Date(),
        question: currentQuestion,
        responseTimeMs,
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (data.cypher) {
        onQuerySubmit(currentQuestion, data.cypher);
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content:
          '⚠️ Maaf, terjadi kesalahan. Pastikan backend Python sedang berjalan.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleEvaluate = (message: Message) => {
    if (message.question && onEvaluateQuery) {
      onEvaluateQuery(
        message.question,
        message.content,
        message.responseTimeMs || 0
      );
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#1a1d29',
      }}
    >
      {/* HEADER */}
      <div
        style={{
          padding: '1.5rem',
          borderBottom: '1px solid #334155',
          background: '#1a1d29',
        }}
      >
        <h1
          style={{
            fontSize: '1.4rem',
            fontWeight: 700,
            color: '#3b82f6',
            margin: 0,
          }}
        >
          Graph RAG Exercise Assistant
        </h1>
        <p
          style={{
            fontSize: '0.85rem',
            color: '#94a3b8',
            marginTop: '0.35rem',
          }}
        >
          Sistem rekomendasi latihan berbasis knowledge graph dan
          Large Language Model.
        </p>

        {/* QUICK PROMPTS – hilang setelah user kirim pertanyaan */}
        {showQuickPrompts && (
          <div
            style={{
              marginTop: '1rem',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}
          >
            {[
              'Berikan saya latihan push day.',
              'Quadriceps itu otot bagian apa?',
              'Apa itu Mechanical Tension?',
              'Apa resiko cedera pada latihan deadlift?',
            ].map(example => (
              <button
                key={example}
                type="button"
                onClick={() => setInput(example)}
                style={{
                  borderRadius: '999px',
                  border: '1px solid #334155',
                  background: '#020617',
                  color: '#e5e7eb',
                  fontSize: '0.78rem',
                  padding: '0.4rem 0.75rem',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  transition:
                    'background 0.15s, border-color 0.15s, transform 0.1s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#111827';
                  e.currentTarget.style.borderColor = '#3b82f6';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = '#020617';
                  e.currentTarget.style.borderColor = '#334155';
                }}
              >
                <span style={{ fontSize: '0.8rem' }}>💡</span>
                <span>{example}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* MESSAGES */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {messages.map(message => (
          <div
            key={message.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
              alignItems:
                message.type === 'user' ? 'flex-end' : 'flex-start',
              animation: 'slideIn 0.3s ease-out',
            }}
          >
            <div
              style={{
                maxWidth: '85%',
                width: '100%',
              }}
            >
              <div
                style={{
                  padding: '1rem 1.25rem',
                  borderRadius: '1rem',
                  lineHeight: '1.6',
                  wordWrap: 'break-word',
                  ...(message.type === 'user'
                    ? {
                        background: '#3b82f6',
                        color: '#ffffff',
                        borderBottomRightRadius: '0.25rem',
                      }
                    : {
                        background: '#1e293b',
                        color: '#ffffff',
                        border: '1px solid #334155',
                        borderBottomLeftRadius: '0.25rem',
                      }),
                }}
              >
                {message.type === 'assistant' ? (
                  <ReactMarkdown
                    components={{
                      p: ({ node, ...props }) => (
                        <p style={{ margin: '0 0 1rem 0' }} {...props} />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3
                          style={{
                            fontSize: '1.125rem',
                            fontWeight: 700,
                            margin: '1.5rem 0 0.75rem 0',
                            color: '#60a5fa',
                          }}
                          {...props}
                        />
                      ),
                      strong: ({ node, ...props }) => (
                        <strong
                          style={{
                            color: '#00ffff',
                            fontWeight: 700,
                          }}
                          {...props}
                        />
                      ),
                      hr: ({ node, ...props }) => (
                        <hr
                          style={{
                            border: 'none',
                            borderTop: '1px solid #334155',
                            margin: '1.5rem 0',
                          }}
                          {...props}
                        />
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>

              {message.type === 'assistant' && (
                <p
                  style={{
                    marginTop: '0.4rem',
                    fontSize: '0.7rem',
                    color: '#6b7280',
                    fontStyle: 'italic',
                  }}
                >
                  *Rangkuman ini dihasilkan dari knowledge graph latihan beban
                  dan literatur ilmiah.*
                </p>
              )}

              {message.type === 'assistant' && message.question && (
                <button
                  onClick={() => handleEvaluate(message)}
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: '#8b5cf6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={e =>
                    (e.currentTarget.style.background = '#7c3aed')
                  }
                  onMouseLeave={e =>
                    (e.currentTarget.style.background = '#8b5cf6')
                  }
                >
                  📊 Evaluate Answer
                </button>
              )}
            </div>

            <span
              style={{
                fontSize: '0.75rem',
                color: '#64748b',
                paddingLeft: '0.5rem',
                paddingRight: '0.5rem',
              }}
            >
              {message.timestamp.toLocaleTimeString('id-ID', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        ))}
        {isLoading && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: '#94a3b8',
              fontSize: '0.875rem',
            }}
          >
            <div
              className="spinner"
              style={{
                width: '16px',
                height: '16px',
                border: '2px solid #334155',
                borderTopColor: '#3b82f6',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}
            />
            <span>Mengetik...</span>
          </div>
        )}
      </div>

      {/* INPUT */}
      <div
        style={{
          padding: '1.5rem',
          borderTop: '1px solid #334155',
          background: '#1a1d29',
        }}
      >
        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'flex-end',
          }}
        >
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tanyakan tentang latihan, anatomi, atau konsep ilmiah..."
            disabled={isLoading}
            style={{
              flex: 1,
              minHeight: '44px',
              maxHeight: '120px',
              padding: '0.75rem 1rem',
              background: '#1e293b',
              border: '2px solid #334155',
              borderRadius: '0.75rem',
              color: '#ffffff',
              fontSize: '0.875rem',
              lineHeight: '1.5',
              resize: 'none',
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
            onFocus={e => (e.target.style.borderColor = '#3b82f6')}
            onBlur={e => (e.target.style.borderColor = '#334155')}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            style={{
              minWidth: '44px',
              height: '44px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background:
                input.trim() && !isLoading ? '#3b82f6' : '#334155',
              color: '#ffffff',
              border: 'none',
              borderRadius: '0.75rem',
              cursor:
                input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s',
              fontWeight: 600,
              padding: '0 1.25rem',
              fontSize: '0.875rem',
            }}
          >
            Kirim
          </button>
        </form>
      </div>
    </div>
  );
}
