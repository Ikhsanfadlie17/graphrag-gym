export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Neo4jNode {
  id: string | number;
  labels: string[];
  properties: Record<string, any>;
}

export interface Neo4jRelationship {
  id: string | number;
  type: string;
  startNode: string | number;
  endNode: string | number;
  properties: Record<string, any>;
}

export interface GraphData {
  nodes: Neo4jNode[];
  relationships: Neo4jRelationship[];
}

export interface QueryResponse {
  answer: string;
  graphData?: GraphData;
}

export interface NeovisConfig {
  containerId: string;
  neo4j: {
    serverUrl: string;
    serverUser: string;
    serverPassword: string;
  };
  visConfig: any;
  labels: Record<string, any>;
  relationships: Record<string, any>;
  initialCypher: string;
}
