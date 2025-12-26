'use client';

import { useEffect, useRef, useState } from 'react';
import cytoscape, { Core } from 'cytoscape';

interface GraphViewProps {
  cypher?: string;
  onNodeClick?: (nodeId: string) => void;
}

export default function GraphView({ cypher, onNodeClick }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch graph data from backend
  const fetchGraphData = async (cypherQuery: string) => {
    try {
      setIsLoading(true);
      setError(null);

      console.log('🔍 Fetching graph data...');

      const response = await fetch('http://localhost:5000/graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cypher: cypherQuery }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`✅ Received ${data.nodes.length} nodes, ${data.edges.length} edges`);

      return data;
    } catch (err) {
      console.error('❌ Fetch error:', err);
      throw err;
    }
  };

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    console.log('🎨 Initializing Cytoscape...');

    const cy = cytoscape({
      container: containerRef.current,

      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            color: '#ffffff',
            'text-outline-color': '#000000',
            'text-outline-width': 3,
            'font-size': '12px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            width: 50,
            height: 50,
            'border-width': 3,
            'border-color': '#000000',
            'overlay-padding': 6,
          },
        },
        {
          selector: 'node[group="Exercise"]',
          style: {
            'background-color': '#3b82f6',
          },
        },
        {
          selector: 'node[group="BodyPart"]',
          style: {
            'background-color': '#ef4444',
          },
        },
        {
          selector: 'node[group="Technique"]',
          style: {
            'background-color': '#14b8a6',
          },
        },
        {
          selector: 'node[group="InjuryRisk"]',
          style: {
            'background-color': '#eab308',
          },
        },
        {
          selector: 'node[group="Equipment"]',
          style: {
            'background-color': '#22c55e',
          },
        },
        {
          selector: 'node[group="ScienceConcept"]',
          style: {
            'background-color': '#a855f7',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 3,
            'line-color': '#64748b',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            color: '#ffffff',
            'text-outline-color': '#000000',
            'text-outline-width': 2,
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
          },
        },
        {
          selector: 'edge[label="TARGETS"]',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444',
          },
        },
        {
          selector: 'edge[label="INVOLVES"]',
          style: {
            'line-color': '#14b8a6',
            'target-arrow-color': '#14b8a6',
          },
        },
        {
          selector: 'edge[label="CAUSES"]',
          style: {
            'line-color': '#eab308',
            'target-arrow-color': '#eab308',
          },
        },
        {
          selector: 'edge[label="USES_EQUIPMENT"]',
          style: {
            'line-color': '#22c55e',
            'target-arrow-color': '#22c55e',
          },
        },
        {
          selector: 'edge[label="SUPPORTED_BY"]',
          style: {
            'line-color': '#a855f7',
            'target-arrow-color': '#a855f7',
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 5,
            'border-color': '#00ffff',
          },
        },
      ],

      layout: {
        name: 'cose',
        idealEdgeLength: 200,
        nodeOverlap: 50,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      },
    });

    // Click event
    cy.on('tap', 'node', evt => {
      const node = evt.target;
      if (onNodeClick) {
        onNodeClick(node.id());
      }
      console.log('🖱️ Node clicked:', node.data());
    });

    cyRef.current = cy;
    setIsLoading(false);

    console.log('✅ Cytoscape initialized');

    return () => {
      cy.destroy();
    };
  }, [onNodeClick]);

  // Update graph when cypher changes
  useEffect(() => {
    if (!cypher || !cyRef.current) return;

    const updateGraph = async () => {
      try {
        console.log('🔄 Updating graph with new cypher...');

        const graphData = await fetchGraphData(cypher);

        const elements = [
          ...graphData.nodes.map((node: any) => ({
            data: {
              id: String(node.id),
              label: node.label,
              color: node.color,
              group: node.group,
            },
          })),
          ...graphData.edges.map((edge: any) => ({
            data: {
              id: `edge-${edge.id}`,
              source: String(edge.from),
              target: String(edge.to),
              label: edge.label,
            },
          })),
        ];

        console.log(`📊 Adding ${elements.length} elements to graph`);

        if (!cyRef.current) {
          console.error('❌ Cytoscape instance not initialized');
          return;
        }

        cyRef.current.elements().remove();
        cyRef.current.add(elements);

        cyRef.current
          .layout({
            name: 'cose',
            idealEdgeLength: 200,
            nodeOverlap: 50,
            refresh: 20,
            fit: true,
            padding: 30,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: 400000,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0,
          })
          .run();

        console.log('✅ Graph updated successfully');
        setIsLoading(false);
      } catch (err) {
        console.error('❌ Update error:', err);
        setError(
          err instanceof Error ? err.message : 'Failed to update graph'
        );
        setIsLoading(false);
      }
    };

    updateGraph();
  }, [cypher]);

  return (
    <div
      className="graph-view-container"
      style={{ width: '100%', height: '100%', position: 'relative' }}
    >
      {/* TITLE */}
      <div
        style={{
          position: 'absolute',
          top: '0.75rem',
          left: '1rem',
          zIndex: 6,
          background: 'rgba(15,23,42,0.85)',
          padding: '0.5rem 0.75rem',
          borderRadius: '0.5rem',
          border: '1px solid #334155',
        }}
      >
        <p
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            color: '#e5e7eb',
            margin: 0,
          }}
        >
          Knowledge Graph Resistance Training
        </p>
        <p
          style={{
            fontSize: '0.7rem',
            color: '#9ca3af',
            margin: '0.15rem 0 0 0',
          }}
        >
          Hubungan Exercise – BodyPart – Equipment – Technique – InjuryRisk – ScienceConcept.
        </p>
      </div>

      {/* LEGEND (CSS sudah di globals.css) */}
      <div className="graph-legend">
        <div className="legend-title">Tipe Node</div>
        <div className="legend-item">
          <span className="legend-color exercise" />
          <span>Exercise</span>
        </div>
        <div className="legend-item">
          <span className="legend-color bodypart" />
          <span>BodyPart</span>
        </div>
        <div className="legend-item">
          <span className="legend-color equipment" />
          <span>Equipment</span>
        </div>
        <div className="legend-item">
          <span className="legend-color technique" />
          <span>Technique</span>
        </div>
        <div className="legend-item">
          <span className="legend-color injury" />
          <span>InjuryRisk</span>
        </div>
        <div className="legend-item">
          <span className="legend-color science" />
          <span>ScienceConcept</span>
        </div>
      </div>

      {isLoading && (
        <div className="graph-loading">
          <div className="spinner"></div>
          <p>Memuat subgraf dari Neo4j…</p>
        </div>
      )}
      {error && (
        <div className="graph-error">
          <p style={{ fontSize: '0.875rem', color: '#f9fafb' }}>{error}</p>
        </div>
      )}
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', background: '#020617' }}
      />
    </div>
  );
}
