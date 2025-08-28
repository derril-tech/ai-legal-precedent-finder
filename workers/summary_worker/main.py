"""
Summary Worker - Main Entry Point

Generates summaries of legal cases.
Handles:
- Holdings extraction
- Reasoning analysis
- Dicta identification
- Summary storage
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
import openai

from .summary_generator import SummaryGenerator
from .content_analyzer import ContentAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks
app = FastAPI(title="Summary Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"
OPENAI_API_KEY = "your-openai-api-key"  # Will be from env
OPENAI_MODEL = "gpt-4"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

content_analyzer = ContentAnalyzer()
summary_generator = SummaryGenerator(openai_api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

async def process_summary_make(msg: Msg):
    """Process summary make message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing summary make: {data.get('case_id', 'unknown')}")
        
        case_id = data.get('case_id')
        workspace_id = data.get('workspace_id')
        
        # Generate summaries
        result = await generate_case_summaries(case_id, workspace_id)
        
        # Publish completion event
        await publish_summary_completed(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing summary make: {e}")
        await msg.nak()

async def generate_case_summaries(
    case_id: str,
    workspace_id: str
) -> Dict[str, Any]:
    """
    Generate summaries for a case
    
    Args:
        case_id: Case identifier
        workspace_id: Workspace context
        
    Returns:
        Dictionary with summary generation results
    """
    try:
        with SessionLocal() as session:
            # Get case and passages
            case_query = text("""
                SELECT id, citation, case_name, court, jurisdiction, text_content
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
            
            # Get passages by section type
            passages_query = text("""
                SELECT id, section_type, content
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
                    'message': 'No passages found to summarize',
                    'summaries_created': 0
                }
            
            # Analyze content and generate summaries
            summaries = []
            
            # Group passages by section type
            holdings_passages = [p for p in passages if p.section_type == 'holdings']
            reasoning_passages = [p for p in passages if p.section_type == 'reasoning']
            dicta_passages = [p for p in passages if p.section_type == 'dicta']
            
            # Generate holdings summary
            if holdings_passages:
                holdings_content = '\n\n'.join([p.content for p in holdings_passages])
                holdings_summary = await summary_generator.generate_holdings_summary(
                    case_name=case_data.case_name,
                    content=holdings_content
                )
                summaries.append({
                    'summary_type': 'holdings',
                    'summary_text': holdings_summary['summary'],
                    'confidence': holdings_summary['confidence']
                })
            
            # Generate reasoning summary
            if reasoning_passages:
                reasoning_content = '\n\n'.join([p.content for p in reasoning_passages])
                reasoning_summary = await summary_generator.generate_reasoning_summary(
                    case_name=case_data.case_name,
                    content=reasoning_content
                )
                summaries.append({
                    'summary_type': 'reasoning',
                    'summary_text': reasoning_summary['summary'],
                    'confidence': reasoning_summary['confidence']
                })
            
            # Generate dicta summary
            if dicta_passages:
                dicta_content = '\n\n'.join([p.content for p in dicta_passages])
                dicta_summary = await summary_generator.generate_dicta_summary(
                    case_name=case_data.case_name,
                    content=dicta_content
                )
                summaries.append({
                    'summary_type': 'dicta',
                    'summary_text': dicta_summary['summary'],
                    'confidence': dicta_summary['confidence']
                })
            
            # Store summaries
            await store_summaries(session, case_id, summaries)
            
            session.commit()
            
            return {
                'case_id': case_id,
                'status': 'success',
                'summaries_created': len(summaries),
                'summary_types': [s['summary_type'] for s in summaries]
            }
            
    except Exception as e:
        logger.error(f"Error generating summaries for case {case_id}: {e}")
        return {
            'case_id': case_id,
            'status': 'error',
            'error': str(e)
        }

async def store_summaries(
    session,
    case_id: str,
    summaries: List[Dict[str, Any]]
):
    """Store summaries in database"""
    
    for summary in summaries:
        summary_query = text("""
            INSERT INTO case_summaries (
                case_id, summary_type, summary_text, confidence
            ) VALUES (
                :case_id, :summary_type, :summary_text, :confidence
            ) ON CONFLICT (case_id, summary_type) DO UPDATE SET
                summary_text = EXCLUDED.summary_text,
                confidence = EXCLUDED.confidence
        """)
        
        session.execute(summary_query, {
            'case_id': case_id,
            'summary_type': summary['summary_type'],
            'summary_text': summary['summary_text'],
            'confidence': summary['confidence']
        })

async def publish_summary_completed(result: Dict[str, Any]):
    """Publish summary completed event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing summary completed event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "summary-worker"}

@app.post("/summaries/generate")
async def manual_generate_summaries(case_id: str, workspace_id: str):
    """Manual summary generation endpoint"""
    result = await generate_case_summaries(case_id, workspace_id)
    return result

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to summary make events
    await nc.subscribe("summary.make", cb=process_summary_make)
    
    logger.info("Summary worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
