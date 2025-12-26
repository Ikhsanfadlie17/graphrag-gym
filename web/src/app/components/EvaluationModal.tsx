'use client';

import { useEffect, useState, useRef } from 'react';

interface EvaluationMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  response_time_ms: number;
  graph_coverage: number;
}

interface EvaluationModalProps {
  question: string;
  answer: string;
  responseTimeMs?: number;
  onClose: () => void;
}

export default function EvaluationModal({ question, answer, responseTimeMs = 0, onClose }: EvaluationModalProps) {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState('Initializing...');
  
  const hasFetched = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMounted = useRef(true); // ✅ Track if component is still mounted

  useEffect(() => {
    isMounted.current = true;
    
    if (hasFetched.current) {
      console.log('⚠️ Evaluation already in progress, skipping...');
      return;
    }

    hasFetched.current = true;
    evaluateQuery();

    return () => {
      console.log('🧹 Cleanup triggered');
      isMounted.current = false;
      
      // ✅ DON'T abort if still loading - let it complete!
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  const evaluateQuery = async () => {
    console.log('🚀 Starting evaluation...');
    console.log('📝 Question:', question);
    console.log('📄 Answer length:', answer.length, 'chars');
    console.log('⏱️ Response time:', responseTimeMs, 'ms');
    
    // Progress indicator
    let elapsed = 0;
    progressIntervalRef.current = setInterval(() => {
      elapsed += 5;
      if (elapsed < 30) {
        setProgress(`Evaluating... ${elapsed}s`);
      } else if (elapsed < 60) {
        setProgress(`Still processing... ${elapsed}s`);
      } else if (elapsed < 120) {
        setProgress(`Almost done... ${elapsed}s`);
      } else {
        setProgress(`Taking longer than usual... ${elapsed}s`);
      }
    }, 5000);
    
    try {
      setLoading(true);
      setError(null);
      
      abortControllerRef.current = new AbortController();
      
      // ✅ 3 minutes timeout
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          console.log('⏰ Request timeout after 180 seconds');
        }
      }, 180000);
      
      console.log('📡 Sending POST request with pre-generated answer...');
      
      const requestStartTime = performance.now();
      
      const response = await fetch('http://localhost:5000/evaluate', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ 
          question,
          answer,
          response_time_ms: responseTimeMs
        }),
        signal: abortControllerRef.current.signal
      });

      const requestEndTime = performance.now();
      const requestDuration = requestEndTime - requestStartTime;
      
      clearTimeout(timeoutId);
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      console.log('📥 Response status:', response.status);
      console.log('⏱️ Request duration:', (requestDuration/1000).toFixed(1), 's');

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response error:', errorText);
        throw new Error(`Evaluation failed (${response.status})`);
      }

      const data = await response.json();
      console.log('✅ Evaluation data received:', data);
      
      if (!data.metrics) {
        throw new Error('Invalid response: missing metrics');
      }

      // ✅ Only set state if component is still mounted
      if (isMounted.current) {
        setMetrics(data.metrics);
        setLoading(false);
        console.log('✅ Evaluation complete!');
      } else {
        console.log('⚠️ Component unmounted, skipping state update');
      }
      
    } catch (err) {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      
      // ✅ Only set error if component is still mounted
      if (!isMounted.current) {
        console.log('⚠️ Component unmounted during error, ignoring');
        return;
      }
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          console.log('⚠️ Request was aborted');
          setError('Request timeout (>180s). The evaluation is taking too long. Please try again.');
        } else {
          console.error('❌ Evaluation error:', err);
          setError(err.message || 'Evaluation failed');
        }
      } else {
        console.error('❌ Unknown error:', err);
        setError('Unknown error occurred');
      }
      
      setLoading(false);
    }
  };

  const handleRetry = () => {
    console.log('🔄 Retrying evaluation...');
    hasFetched.current = false;
    setError(null);
    setMetrics(null);
    setProgress('Initializing...');
    evaluateQuery();
  };

  // ✅ Prevent closing while loading (optional)
  const handleClose = () => {
    if (loading) {
      const confirm = window.confirm('Evaluation is in progress. Are you sure you want to close?');
      if (!confirm) return;
    }
    onClose();
  };

  // ✅ Prevent backdrop click while loading
  const handleBackdropClick = () => {
    if (!loading) {
      onClose();
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.9) return '#22c55e';
    if (score >= 0.7) return '#eab308';
    return '#ef4444';
  };

  const getScoreGrade = (score: number): string => {
    if (score >= 0.9) return 'A';
    if (score >= 0.8) return 'B';
    if (score >= 0.7) return 'C';
    if (score >= 0.6) return 'D';
    return 'F';
  };

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '2rem'
      }} 
      onClick={handleBackdropClick}
    >
      <div 
        style={{
          background: '#1a1d29',
          borderRadius: '1rem',
          padding: '2rem',
          maxWidth: '800px',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          border: '1px solid #334155'
        }} 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '1.5rem'
        }}>
          <div style={{ flex: 1 }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: 'bold',
              color: 'white',
              margin: '0 0 0.5rem 0'
            }}>
              📊 Answer Evaluation
            </h2>
            <p style={{
              fontSize: '0.875rem',
              color: '#94a3b8',
              margin: '0 0 1rem 0',
              padding: '0.75rem',
              background: '#1e293b',
              borderRadius: '0.5rem',
              borderLeft: '3px solid #3b82f6'
            }}>
              <strong style={{ color: '#60a5fa' }}>Question:</strong> {question}
            </p>
          </div>
          <button
            onClick={handleClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: loading ? '#475569' : '#94a3b8',
              fontSize: '1.5rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              padding: '0.5rem',
              marginLeft: '1rem',
              opacity: loading ? 0.5 : 1
            }}
            disabled={loading}
          >
            ✕
          </button>
        </div>

        {/* Loading State */}
        {loading && !metrics && !error && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3rem',
            gap: '1rem'
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              border: '6px solid #334155',
              borderTopColor: '#8b5cf6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />
            <p style={{ 
              color: '#94a3b8', 
              fontSize: '1rem',
              fontWeight: '600',
              margin: 0
            }}>
              {progress}
            </p>
            <p style={{ 
              color: '#64748b', 
              fontSize: '0.875rem',
              textAlign: 'center',
              margin: 0,
              maxWidth: '400px'
            }}>
              Running LLM evaluations<br/>
              This typically takes 30-60 seconds<br/>
              <span style={{ fontSize: '0.75rem', color: '#475569' }}>
                Please keep this window open
              </span>
            </p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{
            padding: '1.5rem',
            background: '#7f1d1d',
            border: '1px solid #991b1b',
            borderRadius: '0.5rem',
            color: '#fca5a5'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'flex-start',
              gap: '0.75rem',
              marginBottom: '1rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>⚠️</span>
              <div>
                <h3 style={{ 
                  margin: '0 0 0.5rem 0',
                  fontSize: '1rem',
                  fontWeight: 'bold'
                }}>
                  Evaluation Failed
                </h3>
                <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: '1.5' }}>{error}</p>
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              gap: '0.75rem'
            }}>
              <button
                onClick={handleRetry}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '600'
                }}
              >
                🔄 Retry
              </button>
              <button
                onClick={onClose}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#334155',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                Close
              </button>
            </div>
          </div>
        )}

        {/* Success State */}
        {metrics && !loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '1rem'
            }}>
              <MetricCard
                icon="🎯"
                title="Faithfulness"
                score={metrics.faithfulness}
                description="Data accuracy"
                getScoreColor={getScoreColor}
                getScoreGrade={getScoreGrade}
              />
              <MetricCard
                icon="📈"
                title="Relevancy"
                score={metrics.answer_relevancy}
                description="Answer quality"
                getScoreColor={getScoreColor}
                getScoreGrade={getScoreGrade}
              />
              <MetricCard
                icon="💾"
                title="Precision"
                score={metrics.context_precision}
                description="Retrieval accuracy"
                getScoreColor={getScoreColor}
                getScoreGrade={getScoreGrade}
              />
              <div style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.75rem',
                padding: '1rem'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.75rem'
                }}>
                  <span>⏱️</span>
                  <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                    Response Time
                  </span>
                </div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 'bold',
                  color: '#3b82f6'
                }}>
                  {(metrics.response_time_ms / 1000).toFixed(1)}s
                </div>
                <div style={{
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  marginTop: '0.25rem'
                }}>
                  Graph Coverage: {(metrics.graph_coverage * 100).toFixed(2)}%
                </div>
              </div>
            </div>

            <div style={{
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(168, 85, 247, 0.2))',
              border: '1px solid #334155',
              borderRadius: '0.75rem',
              padding: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <h3 style={{
                  fontSize: '1.125rem',
                  fontWeight: 'bold',
                  color: 'white',
                  margin: '0 0 0.25rem 0'
                }}>
                  Overall Grade
                </h3>
                <p style={{
                  fontSize: '0.875rem',
                  color: '#94a3b8',
                  margin: 0
                }}>
                  Based on comprehensive evaluation
                </p>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontSize: '3rem',
                  fontWeight: 'bold',
                  color: 'white'
                }}>
                  {getScoreGrade(
                    (metrics.faithfulness + metrics.answer_relevancy + metrics.context_precision) / 3
                  )}
                </div>
                <span style={{
                  fontSize: '0.75rem',
                  color: '#94a3b8'
                }}>
                  {((
                    (metrics.faithfulness + metrics.answer_relevancy + metrics.context_precision) / 3
                  ) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ icon, title, score, description, getScoreColor, getScoreGrade }: any) {
  return (
    <div style={{
      background: '#1e293b',
      border: '1px solid #334155',
      borderRadius: '0.75rem',
      padding: '1rem'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.75rem'
      }}>
        <span>{icon}</span>
        <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
          {title}
        </span>
      </div>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '0.5rem',
        marginBottom: '0.5rem'
      }}>
        <span style={{
          fontSize: '1.5rem',
          fontWeight: 'bold',
          color: getScoreColor(score)
        }}>
          {(score * 100).toFixed(1)}%
        </span>
        <span style={{
          fontSize: '0.75rem',
          background: 'rgba(148, 163, 184, 0.2)',
          padding: '0.25rem 0.5rem',
          borderRadius: '0.25rem',
          color: '#e2e8f0'
        }}>
          {getScoreGrade(score)}
        </span>
      </div>
      <div style={{
        background: '#334155',
        height: '6px',
        borderRadius: '9999px',
        overflow: 'hidden'
      }}>
        <div style={{
          background: getScoreColor(score),
          height: '100%',
          width: `${score * 100}%`,
          transition: 'width 0.5s ease'
        }} />
      </div>
      <p style={{
        fontSize: '0.75rem',
        color: '#64748b',
        margin: '0.5rem 0 0 0'
      }}>
        {description}
      </p>
    </div>
  );
}
