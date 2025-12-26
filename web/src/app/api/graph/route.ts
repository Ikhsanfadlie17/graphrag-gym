import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { cypher } = await request.json();

    if (!cypher || typeof cypher !== 'string') {
      return NextResponse.json(
        { error: 'Cypher query is required and must be a string' },
        { status: 400 }
      );
    }

    const pythonBackendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:5000';

    const response = await fetch(`${pythonBackendUrl}/graph`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ cypher }),
    });

    if (!response.ok) {
      throw new Error(`Python backend responded with status: ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json({
      nodes: data.nodes || [],
      relationships: data.relationships || [],
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Error fetching graph data:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch graph data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json(
    { message: 'Use POST method with { cypher: string } in body' },
    { status: 405 }
  );
}
