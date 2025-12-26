'use client';

import { ReactNode, useState, useCallback } from 'react';

interface ResizableLayoutProps {
  leftPanel: ReactNode;
  rightPanel: ReactNode;
}

export default function ResizableLayout({ leftPanel, rightPanel }: ResizableLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(60); // persen

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    const startX = e.clientX;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const container = document.documentElement; // full viewport width
      const containerWidth = container.clientWidth;

      const deltaPercent = (deltaX / containerWidth) * 100;
      setLeftWidth(prev => {
        const next = Math.min(80, Math.max(30, prev + deltaPercent)); // batas 30–80%
        return next;
      });
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, []);

  const rightWidth = 100 - leftWidth;

  return (
    <div
      style={{
        display: 'flex',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: '#0f1419',
        userSelect: 'none',
      }}
    >
      {/* LEFT PANEL - Graph */}
      <div
        style={{
          flexBasis: `${leftWidth}%`,
          flexGrow: 0,
          flexShrink: 0,
          height: '100%',
          overflow: 'hidden',
          background: '#1a1d29',
          position: 'relative',
        }}
      >
        {leftPanel}
      </div>

      {/* RESIZE HANDLE */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          width: '4px',
          cursor: 'col-resize',
          background: '#334155',
          transition: 'background 0.2s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6')}
        onMouseLeave={e => (e.currentTarget.style.background = '#334155')}
      />

      {/* RIGHT PANEL - Chat */}
      <div
        style={{
          flexBasis: `${rightWidth}%`,
          flexGrow: 0,
          flexShrink: 0,
          height: '100%',
          overflow: 'hidden',
          borderLeft: '1px solid #334155',
          background: '#1a1d29',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {rightPanel}
      </div>
    </div>
  );
}
