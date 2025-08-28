"""
Graph Worker - Main Entry Point

Builds precedent graphs from case citations.
Handles:
- Citation extraction and relationship detection
- Directed graph construction
- Treatment type classification (follow, overrule, distinguish)
- Graph visualization data
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import networkx as nx

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
import neo4j

from .graph_builder import PrecedentGraphBuilder
from .relationship_extractor import RelationshipExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks
app = FastAPI(title="Graph Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"
NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

neo4j_driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

relationship_extractor = RelationshipExtractor()
graph_builder = PrecedentGraphBuilder(engine, neo4j_driver)

async def process_graph_update(msg: Msg):
    """Process graph update message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing graph update: {data.get('case_id', 'unknown')}")
        
        case_id = data.get('case_id')
        workspace_id = data.get('workspace_id')
        
        # Build or update the graph
        result = await build_precedent_graph(case_id, workspace_id)
        
        # Publish completion event
        await publish_graph_completed(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing graph update: {e}")
        await msg.nak()

async def build_precedent_graph(
    case_id: str,
    workspace_id: str
) -> Dict[str, Any]:
    """
    Build precedent graph for a case
    
    Args:
        case_id: Case identifier
        workspace_id: Workspace context
        
    Returns:
        Dictionary with graph building results
    """
    try:
        with SessionLocal() as session:
            # Get case and its citations
            case_query = text("""
                SELECT id, citation, case_name, court, jurisdiction, decision_date
                FROM cases 
                WHERE id = :case_id AND workspace_id = :workspace_id
            """)
            
            case_result = session.execute(case_query, {
                'case_id': case_id,
                'workspace_id': workspace_id
            })
            case_data = case_result.fetchone()
            
            if not case_data:
                raise ValueError(f"Case {case_id} not found in workspace {workspace_id}")
            
            # Extract relationships from case citations
            relationships = await relationship_extractor.extract_relationships(
                case_id=case_id,
                session=session
            )
            
            if not relationships:
                return {
                    'case_id': case_id,
                    'status': 'success',
                    'message': 'No relationships found',
                    'nodes_created': 0,
                    'edges_created': 0
                }
            
            # Build the graph
            graph_result = await graph_builder.build_graph(
                case_id=case_id,
                relationships=relationships,
                workspace_id=workspace_id
            )
            
            # Store graph metadata
            await store_graph_metadata(
                session=session,
                case_id=case_id,
                graph_result=graph_result
            )
            
            session.commit()
            
            return {
                'case_id': case_id,
                'status': 'success',
                'nodes_created': graph_result['nodes_created'],
                'edges_created': graph_result['edges_created'],
                'graph_id': graph_result['graph_id']
            }
            
    except Exception as e:
        logger.error(f"Error building precedent graph for case {case_id}: {e}")
        return {
            'case_id': case_id,
            'status': 'error',
            'error': str(e)
        }

async def store_graph_metadata(
    session,
    case_id: str,
    graph_result: Dict[str, Any]
):
    """Store graph metadata in database"""
    
    # Insert graph node
    node_query = text("""
        INSERT INTO precedent_graph_nodes (
            case_id, node_type, properties
        ) VALUES (
            :case_id, 'case', :properties
        ) ON CONFLICT (case_id) DO UPDATE SET
            properties = EXCLUDED.properties
    """)
    
    properties = {
        'graph_id': graph_result['graph_id'],
        'nodes_count': graph_result['nodes_created'],
        'edges_count': graph_result['edges_created'],
        'built_at': datetime.utcnow().isoformat()
    }
    
    session.execute(node_query, {
        'case_id': case_id,
        'properties': json.dumps(properties)
    })

async def publish_graph_completed(result: Dict[str, Any]):
    """Publish graph completed event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing graph completed event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "graph-worker"}

@app.post("/graphs/build")
async def manual_build_graph(case_id: str, workspace_id: str):
    """Manual graph building endpoint"""
    result = await build_precedent_graph(case_id, workspace_id)
    return result

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to graph update events
    await nc.subscribe("graph.update", cb=process_graph_update)
    
    logger.info("Graph worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()
        neo4j_driver.close()

if __name__ == "__main__":
    asyncio.run(main())
