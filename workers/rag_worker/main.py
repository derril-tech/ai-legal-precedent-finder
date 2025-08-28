"""
RAG Worker - Main Entry Point

Retrieval-Augmented Generation for legal Q&A with citations-first decoding.
Handles:
- Hybrid retrieval (BM25 + dense)
- Reranking
- Grounded answer generation
- Inline citations
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

from .retriever import HybridRetriever
from .generator import CitationsFirstGenerator
from .planner import AnswerPlanner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks
app = FastAPI(title="RAG Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"
OPENAI_API_KEY = "your-openai-api-key"  # Will be from env
OPENAI_MODEL = "gpt-4"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

retriever = HybridRetriever(engine)
planner = AnswerPlanner()
generator = CitationsFirstGenerator(openai_api_key=OPENAI_API_KEY, model=OPENAI_MODEL)

async def process_qa_ask(msg: Msg):
    """Process QA ask message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing QA ask: {data.get('session_id', 'unknown')}")
        
        session_id = data.get('session_id')
        question = data.get('question')
        workspace_id = data.get('workspace_id')
        
        # Process the question
        result = await answer_question(session_id, question, workspace_id)
        
        # Publish completion event
        await publish_qa_completed(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing QA ask: {e}")
        await msg.nak()

async def answer_question(
    session_id: str,
    question: str,
    workspace_id: str
) -> Dict[str, Any]:
    """
    Answer a legal question using RAG
    
    Args:
        session_id: QA session identifier
        question: Legal question to answer
        workspace_id: Workspace context
        
    Returns:
        Dictionary with answer and citations
    """
    try:
        # Step 1: Retrieve relevant passages
        passages = await retriever.retrieve(
            query=question,
            workspace_id=workspace_id,
            top_k=20
        )
        
        if not passages:
            # No relevant passages found
            return await handle_no_precedent_found(session_id, question)
        
        # Step 2: Rerank passages
        reranked_passages = await retriever.rerank(question, passages, top_k=10)
        
        # Step 3: Plan answer structure
        plan = await planner.plan_answer(question, reranked_passages)
        
        # Step 4: Generate grounded answer with citations
        answer_result = await generator.generate_answer(
            question=question,
            passages=reranked_passages,
            plan=plan
        )
        
        # Step 5: Store answer and citations
        result = await store_answer_and_citations(
            session_id=session_id,
            answer_text=answer_result['answer'],
            reasoning=answer_result['reasoning'],
            citations=answer_result['citations'],
            confidence=answer_result['confidence']
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return await handle_error(session_id, question, str(e))

async def handle_no_precedent_found(session_id: str, question: str) -> Dict[str, Any]:
    """Handle case when no relevant precedent is found"""
    
    answer_text = (
        "I could not find any relevant legal precedent to answer your question. "
        "This may be because:\n\n"
        "1. The question involves a novel legal issue with limited case law\n"
        "2. The specific jurisdiction or context is not covered in our database\n"
        "3. The question may require consultation with current statutes or regulations\n\n"
        "I recommend consulting with a qualified legal professional for guidance on this matter."
    )
    
    return await store_answer_and_citations(
        session_id=session_id,
        answer_text=answer_text,
        reasoning="No relevant precedent found in database",
        citations=[],
        confidence=0.0
    )

async def handle_error(session_id: str, question: str, error: str) -> Dict[str, Any]:
    """Handle errors in QA processing"""
    
    answer_text = (
        "I encountered an error while processing your question. "
        "Please try rephrasing your question or contact support if the issue persists."
    )
    
    return await store_answer_and_citations(
        session_id=session_id,
        answer_text=answer_text,
        reasoning=f"Error occurred: {error}",
        citations=[],
        confidence=0.0
    )

async def store_answer_and_citations(
    session_id: str,
    answer_text: str,
    reasoning: str,
    citations: List[Dict[str, Any]],
    confidence: float
) -> Dict[str, Any]:
    """Store answer and citations in database"""
    
    with SessionLocal() as session:
        try:
            # Update QA session status
            update_session_query = text("""
                UPDATE qa_sessions 
                SET status = 'completed', updated_at = NOW()
                WHERE id = :session_id
            """)
            session.execute(update_session_query, {'session_id': session_id})
            
            # Insert answer
            answer_query = text("""
                INSERT INTO answers (
                    qa_session_id, answer_text, reasoning, confidence
                ) VALUES (
                    :session_id, :answer_text, :reasoning, :confidence
                ) RETURNING id
            """)
            
            answer_result = session.execute(answer_query, {
                'session_id': session_id,
                'answer_text': answer_text,
                'reasoning': reasoning,
                'confidence': confidence
            })
            
            answer_id = answer_result.fetchone()[0]
            
            # Insert citations
            for citation in citations:
                citation_query = text("""
                    INSERT INTO answer_citations (
                        answer_id, case_id, passage_id, citation_text, relevance_score
                    ) VALUES (
                        :answer_id, :case_id, :passage_id, :citation_text, :relevance_score
                    )
                """)
                
                session.execute(citation_query, {
                    'answer_id': answer_id,
                    'case_id': citation['case_id'],
                    'passage_id': citation.get('passage_id'),
                    'citation_text': citation['citation_text'],
                    'relevance_score': citation.get('relevance_score', 0.0)
                })
            
            session.commit()
            
            return {
                'session_id': session_id,
                'answer_id': answer_id,
                'status': 'success',
                'answer_text': answer_text,
                'citations_count': len(citations),
                'confidence': confidence
            }
            
        except Exception as e:
            session.rollback()
            raise e

async def publish_qa_completed(result: Dict[str, Any]):
    """Publish QA completed event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing QA completed event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "rag-worker"}

@app.post("/answer")
async def manual_answer(question: str, workspace_id: str):
    """Manual answer endpoint"""
    session_id = "manual-" + datetime.utcnow().isoformat()
    result = await answer_question(session_id, question, workspace_id)
    return result

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to QA ask events
    await nc.subscribe("qa.ask", cb=process_qa_ask)
    
    logger.info("RAG worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
