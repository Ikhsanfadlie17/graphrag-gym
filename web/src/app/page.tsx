'use client';

import { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import GraphView from './components/GraphView';
import ResizableLayout from './components/ResizableLayout';
import EvaluationModal from './components/EvaluationModal';

export default function Home() {
  const [currentCypher, setCurrentCypher] = useState('');
  const [graphKey, setGraphKey] = useState(0);
  const [evaluationData, setEvaluationData] = useState<{
    question: string;
    answer: string;
    responseTimeMs: number;
  } | null>(null);

  const handleQuerySubmit = (query: string, cypher: string) => {
    console.log('📊 New query:', query);
    console.log('🔍 New cypher:', cypher);
    
    setCurrentCypher(cypher);
    setGraphKey(prev => prev + 1);
  };

  const handleEvaluateQuery = (question: string, answer: string, responseTimeMs: number) => {
    console.log('📊 Evaluate request:');
    console.log('  Question:', question);
    console.log('  Answer length:', answer.length);
    console.log('  Response time:', responseTimeMs, 'ms');
    
    setEvaluationData({ question, answer, responseTimeMs });
  };

  return (
    <>
      <ResizableLayout
        leftPanel={
          <GraphView 
            cypher={currentCypher}
            key={graphKey}
          />
        }
        rightPanel={
          <ChatPanel 
            onQuerySubmit={handleQuerySubmit}
            onEvaluateQuery={handleEvaluateQuery}
          />
        }
      />
      
      {evaluationData && (
        <EvaluationModal
          question={evaluationData.question}
          answer={evaluationData.answer}
          responseTimeMs={evaluationData.responseTimeMs}
          onClose={() => setEvaluationData(null)}
        />
      )}
    </>
  );
}
