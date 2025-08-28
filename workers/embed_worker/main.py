"""
Embed Worker - Main Entry Point

Generates embeddings for legal text and indexes them in pgvector.
Handles:
- Paragraph embeddings
- Holdings embeddings  
- Citation embeddings
- Hybrid search indexing
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json
import numpy as np
from datetime import datetime

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import openai

from .embedding_service import EmbeddingService
from .indexer import VectorIndexer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks
app = FastAPI(title="Embed Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"
OPENAI_API_KEY = "your-openai-api-key"  # Will be from env
OPENAI_MODEL = "text-embedding-ada-002"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize embedding models
embedding_service = EmbeddingService(
    openai_api_key=OPENAI_API_KEY,
    openai_model=OPENAI_MODEL
)
vector_indexer = VectorIndexer(engine)

async def process_index_upsert(msg: Msg):
    """Process index upsert message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing index upsert: {data.get('case_id', 'unknown')}")
        
        case_id = data.get('case_id')
        passage_ids = data.get('passage_ids', [])
        
        # Process the embeddings
        result = await generate_and_index_embeddings(case_id, passage_ids)
        
        # Publish completion event
        await publish_embeddings_completed(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing index upsert: {e}")
        await msg.nak()

async def generate_and_index_embeddings(
    case_id: str, 
    passage_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate embeddings for case passages and index them
    
    Args:
        case_id: Case identifier
        passage_ids: Specific passage IDs to process (None for all)
        
    Returns:
        Dictionary with indexing results
    """
    try:
        with SessionLocal() as session:
            # Get passages to embed
            if passage_ids:
                passages_query = text("""
                    SELECT id, case_id, passage_number, section_type, content, metadata
                    FROM passages 
                    WHERE case_id = :case_id AND id = ANY(:passage_ids)
                    ORDER BY passage_number
                """)
                passages_result = session.execute(passages_query, {
                    'case_id': case_id,
                    'passage_ids': passage_ids
                })
            else:
                passages_query = text("""
                    SELECT id, case_id, passage_number, section_type, content, metadata
                    FROM passages 
                    WHERE case_id = :case_id
                    ORDER BY passage_number
                """)
                passages_result = session.execute(passages_query, {'case_id': case_id})
            
            passages = passages_result.fetchall()
            
            if not passages:
                return {
                    'case_id': case_id,
                    'status': 'success',
                    'message': 'No passages found to embed',
                    'embeddings_created': 0
                }
            
            # Generate embeddings
            embeddings_data = []
            for passage in passages:
                # Generate embedding
                embedding = await embedding_service.generate_embedding(passage.content)
                
                embeddings_data.append({
                    'passage_id': passage.id,
                    'embedding': embedding,
                    'metadata': {
                        'section_type': passage.section_type,
                        'passage_number': passage.passage_number,
                        'case_id': passage.case_id
                    }
                })
            
            # Index embeddings in pgvector
            await vector_indexer.index_embeddings(embeddings_data)
            
            # Update passage metadata with embedding info
            for passage in passages:
                update_query = text("""
                    UPDATE passages 
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb), 
                        '{embedding}', 
                        :embedding_metadata
                    )
                    WHERE id = :passage_id
                """)
                
                embedding_metadata = {
                    'embedded_at': datetime.utcnow().isoformat(),
                    'embedding_model': OPENAI_MODEL,
                    'embedding_dimension': len(embeddings_data[0]['embedding'])
                }
                
                session.execute(update_query, {
                    'passage_id': passage.id,
                    'embedding_metadata': json.dumps(embedding_metadata)
                })
            
            session.commit()
            
            return {
                'case_id': case_id,
                'status': 'success',
                'embeddings_created': len(embeddings_data),
                'passage_ids': [p.id for p in passages]
            }
            
    except Exception as e:
        logger.error(f"Error generating embeddings for case {case_id}: {e}")
        return {
            'case_id': case_id,
            'status': 'error',
            'error': str(e)
        }

async def publish_embeddings_completed(result: Dict[str, Any]):
    """Publish embeddings completed event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing embeddings completed event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "embed-worker"}

@app.post("/embed/{case_id}")
async def manual_embed(case_id: str, passage_ids: Optional[List[str]] = None):
    """Manual embedding endpoint"""
    result = await generate_and_index_embeddings(case_id, passage_ids)
    return result

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to index upsert events
    await nc.subscribe("index.upsert", cb=process_index_upsert)
    
    logger.info("Embed worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
