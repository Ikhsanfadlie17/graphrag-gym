'use client';

import React, { useState, useEffect } from 'react';

interface EvaluationMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  response_time_ms: number;
  graph_coverage: number;
}

interface EvaluationResult {
  total_queries: number;
  timestamp: string;
  average_metrics: EvaluationMetrics;
  individual_results?: any[];
}

export default function EvaluationPanel() {
  const [metrics, setMetrics] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLatestMetrics();
  }, []);

  const fetchLatestMetrics = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5000/metrics/latest');
      
      if (!response.ok) {
        throw new Error('Failed to fetch metrics');
      }
      
      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '400px',
        background: '#1a1d29'
      }}>
        <div style={{
          width: '48px',
          height: '48px',
          border: '4px solid #334155',
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '1rem',
        background: '#7f1d1d',
        border: '1px solid #991b1b',
        borderRadius: '0.5rem',
        color: '#fca5a5',
        margin: '1rem'
      }}>
        <p style={{ margin: 0 }}>Error: {error}</p>
        <button 
          onClick={fetchLatestMetrics}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            background: '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div style={{
        padding: '1rem',
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.5rem',
        color: '#94a3b8',
        margin: '1rem'
      }}>
        <p style={{ margin: 0 }}>No evaluation data available</p>
      </div>
    );
  }

  const { average_metrics, total_queries, timestamp } = metrics;

  return (
    <div style={{
      padding: '2rem',
      background: '#1a1d29',
      minHeight: '100vh',
      color: 'white'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{
          fontSize: '2rem',
          fontWeight: 'bold',
          margin: '0 0 0.5rem 0'
        }}>
          Evaluation Metrics
        </h2>
        <p style={{
          color: '#94a3b8',
          margin: '0 0 0.5rem 0'
        }}>
          Performance analysis based on {total_queries} test queries
        </p>
        <p style={{
          fontSize: '0.875rem',
          color: '#64748b',
          margin: 0
        }}>
          Last updated: {new Date(timestamp).toLocaleString('id-ID')}
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        {/* Faithfulness */}
        <MetricCard
          icon="🎯"
          title="Faithfulness"
          score={average_metrics.faithfulness}
          description="Data accuracy score"
          getScoreColor={getScoreColor}
          getScoreGrade={getScoreGrade}
        />

        {/* Answer Relevancy */}
        <MetricCard
          icon="📈"
          title="Relevancy"
          score={average_metrics.answer_relevancy}
          description="Answer quality score"
          getScoreColor={getScoreColor}
          getScoreGrade={getScoreGrade}
        />

        {/* Context Precision */}
        <MetricCard
          icon="💾"
          title="Precision"
          score={average_metrics.context_precision}
          description="Retrieval accuracy"
          getScoreColor={getScoreColor}
          getScoreGrade={getScoreGrade}
        />

        {/* Response Time */}
        <div style={{
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '1rem'
          }}>
            <span style={{ fontSize: '1.25rem' }}>⏱️</span>
            <span style={{
              fontSize: '0.875rem',
              color: '#94a3b8',
              fontWeight: '500'
            }}>
              Response Time
            </span>
          </div>
          <div style={{
            fontSize: '2rem',
            fontWeight: 'bold',
            color: '#3b82f6',
            marginBottom: '0.5rem'
          }}>
            {(average_metrics.response_time_ms / 1000).toFixed(1)}s
          </div>
          <div style={{
            background: '#334155',
            height: '8px',
            borderRadius: '9999px',
            overflow: 'hidden',
            marginBottom: '0.5rem'
          }}>
            <div style={{
              background: '#3b82f6',
              height: '100%',
              width: `${Math.min((average_metrics.response_time_ms / 30000) * 100, 100)}%`,
              transition: 'width 0.3s ease'
            }} />
          </div>
          <p style={{
            fontSize: '0.75rem',
            color: '#94a3b8',
            margin: 0
          }}>
            Average latency
          </p>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <div style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '0.75rem',
        padding: '1.5rem',
        marginBottom: '2rem'
      }}>
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: 'bold',
          margin: '0 0 0.5rem 0'
        }}>
          Performance Breakdown
        </h3>
        <p style={{
          color: '#94a3b8',
          fontSize: '0.875rem',
          margin: '0 0 1.5rem 0'
        }}>
          Detailed analysis of system performance
        </p>

        {/* Graph Coverage */}
        <div style={{
          background: 'rgba(71, 85, 105, 0.3)',
          padding: '1rem',
          borderRadius: '0.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem'
        }}>
          <div>
            <p style={{
              fontSize: '0.875rem',
              fontWeight: '500',
              color: '#e2e8f0',
              margin: '0 0 0.25rem 0'
            }}>
              Graph Coverage
            </p>
            <p style={{
              fontSize: '0.75rem',
              color: '#94a3b8',
              margin: 0
            }}>
              Percentage of knowledge graph used per query
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{
              fontSize: '1.5rem',
              fontWeight: 'bold',
              color: '#a855f7',
              margin: '0 0 0.25rem 0'
            }}>
              {(average_metrics.graph_coverage * 100).toFixed(2)}%
            </p>
            <span style={{
              fontSize: '0.75rem',
              color: '#94a3b8',
              background: 'rgba(168, 85, 247, 0.2)',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem'
            }}>
              Efficient
            </span>
          </div>
        </div>

        {/* Score Interpretation */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '0.75rem',
          marginTop: '1rem'
        }}>
          <ScoreInterpretation
            color="#22c55e"
            label="✓ Excellent (>90%)"
            description="Production ready"
          />
          <ScoreInterpretation
            color="#eab308"
            label="⚠ Good (70-90%)"
            description="Minor improvements needed"
          />
          <ScoreInterpretation
            color="#ef4444"
            label="✗ Needs Work (<70%)"
            description="Requires optimization"
          />
        </div>
      </div>

      {/* Overall Grade */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(168, 85, 247, 0.3) 100%)',
        border: '1px solid #334155',
        borderRadius: '0.75rem',
        padding: '1.5rem'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <h3 style={{
              fontSize: '1.5rem',
              fontWeight: 'bold',
              margin: '0 0 0.5rem 0'
            }}>
              Overall System Grade
            </h3>
            <p style={{
              color: '#e2e8f0',
              margin: 0
            }}>
              Based on comprehensive evaluation metrics
            </p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '4rem',
              fontWeight: 'bold',
              marginBottom: '0.5rem'
            }}>
              {getScoreGrade(
                (average_metrics.faithfulness + 
                 average_metrics.answer_relevancy + 
                 average_metrics.context_precision) / 3
              )}
            </div>
            <span style={{
              fontSize: '0.875rem',
              background: 'rgba(148, 163, 184, 0.2)',
              padding: '0.5rem 1rem',
              borderRadius: '0.375rem'
            }}>
              {((
                (average_metrics.faithfulness + 
                 average_metrics.answer_relevancy + 
                 average_metrics.context_precision) / 3
              ) * 100).toFixed(1)}% Overall Score
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Components
function MetricCard({ 
  icon, 
  title, 
  score, 
  description, 
  getScoreColor, 
  getScoreGrade 
}: {
  icon: string;
  title: string;
  score: number;
  description: string;
  getScoreColor: (score: number) => string;
  getScoreGrade: (score: number) => string;
}) {
  return (
    <div style={{
      background: '#1e293b',
      border: '1px solid #334155',
      borderRadius: '0.75rem',
      padding: '1.5rem'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '1rem'
      }}>
        <span style={{ fontSize: '1.25rem' }}>{icon}</span>
        <span style={{
          fontSize: '0.875rem',
          color: '#94a3b8',
          fontWeight: '500'
        }}>
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
          fontSize: '2rem',
          fontWeight: 'bold',
          color: getScoreColor(score)
        }}>
          {(score * 100).toFixed(1)}%
        </span>
        <span style={{
          fontSize: '0.875rem',
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
        height: '8px',
        borderRadius: '9999px',
        overflow: 'hidden',
        marginBottom: '0.5rem'
      }}>
        <div style={{
          background: getScoreColor(score),
          height: '100%',
          width: `${score * 100}%`,
          transition: 'width 0.3s ease'
        }} />
      </div>
      <p style={{
        fontSize: '0.75rem',
        color: '#94a3b8',
        margin: 0
      }}>
        {description}
      </p>
    </div>
  );
}

function ScoreInterpretation({ 
  color, 
  label, 
  description 
}: {
  color: string;
  label: string;
  description: string;
}) {
  return (
    <div style={{
      padding: '0.75rem',
      background: `${color}20`,
      border: `1px solid ${color}`,
      borderRadius: '0.5rem'
    }}>
      <p style={{
        fontSize: '0.75rem',
        fontWeight: '500',
        color: color,
        margin: '0 0 0.25rem 0'
      }}>
        {label}
      </p>
      <p style={{
        fontSize: '0.75rem',
        color: '#94a3b8',
        margin: 0
      }}>
        {description}
      </p>
    </div>
  );
}
