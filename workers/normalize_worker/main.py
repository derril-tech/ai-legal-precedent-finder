"""
Normalize Worker - Main Entry Point

Canonicalizes legal data:
- Citations (Bluebook format)
- Party names
- Court names
- Outcomes
- Dates
"""

import asyncio
import logging
from typing import Dict, Any, List
import json
import re
from datetime import datetime

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI

from .normalizer import CitationNormalizer, CourtNormalizer, OutcomeNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks
app = FastAPI(title="Normalize Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

citation_normalizer = CitationNormalizer()
court_normalizer = CourtNormalizer()
outcome_normalizer = OutcomeNormalizer()

async def process_case_normalize(msg: Msg):
    """Process case normalization message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing case normalize: {data.get('case_id', 'unknown')}")
        
        case_id = data.get('case_id')
        
        # Normalize the case
        result = await normalize_case(case_id)
        
        # Publish completion event
        await publish_case_normalized(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing case normalize: {e}")
        await msg.nak()

async def normalize_case(case_id: str) -> Dict[str, Any]:
    """
    Normalize case data
    
    Args:
        case_id: Case identifier
        
    Returns:
        Dictionary with normalization results
    """
    try:
        with SessionLocal() as session:
            # Get case data
            case_query = text("""
                SELECT id, citation, court, jurisdiction, case_name, parties, 
                       outcome, decision_date, opinion_date, judge, metadata
                FROM cases 
                WHERE id = :case_id
            """)
            
            case_result = session.execute(case_query, {'case_id': case_id})
            case_data = case_result.fetchone()
            
            if not case_data:
                raise ValueError(f"Case {case_id} not found")
            
            # Normalize citation
            normalized_citation = citation_normalizer.normalize(case_data.citation)
            
            # Normalize court
            normalized_court = court_normalizer.normalize(case_data.court)
            
            # Normalize outcome
            normalized_outcome = outcome_normalizer.normalize(case_data.outcome)
            
            # Normalize parties
            normalized_parties = normalize_parties(case_data.parties)
            
            # Normalize judge
            normalized_judge = normalize_judge(case_data.judge)
            
            # Update case with normalized data
            update_query = text("""
                UPDATE cases 
                SET citation = :citation,
                    court = :court,
                    outcome = :outcome,
                    parties = :parties,
                    judge = :judge,
                    metadata = jsonb_set(metadata, '{normalized}', :normalized_metadata),
                    updated_at = NOW()
                WHERE id = :case_id
            """)
            
            normalized_metadata = {
                'original_citation': case_data.citation,
                'original_court': case_data.court,
                'original_outcome': case_data.outcome,
                'normalized_at': datetime.utcnow().isoformat()
            }
            
            session.execute(update_query, {
                'case_id': case_id,
                'citation': normalized_citation,
                'court': normalized_court,
                'outcome': normalized_outcome,
                'parties': normalized_parties,
                'judge': normalized_judge,
                'normalized_metadata': json.dumps(normalized_metadata)
            })
            
            # Normalize citations in passages
            await normalize_passage_citations(session, case_id)
            
            session.commit()
            
            return {
                'case_id': case_id,
                'status': 'success',
                'normalized_citation': normalized_citation,
                'normalized_court': normalized_court,
                'normalized_outcome': normalized_outcome
            }
            
    except Exception as e:
        logger.error(f"Error normalizing case {case_id}: {e}")
        return {
            'case_id': case_id,
            'status': 'error',
            'error': str(e)
        }

def normalize_parties(parties: str) -> str:
    """Normalize party names"""
    if not parties:
        return parties
    
    # Remove extra whitespace
    parties = re.sub(r'\s+', ' ', parties.strip())
    
    # Standardize common party abbreviations
    party_mappings = {
        'plaintiff': 'Pl.',
        'defendant': 'Def.',
        'appellant': 'Appellant',
        'appellee': 'Appellee',
        'petitioner': 'Petitioner',
        'respondent': 'Respondent'
    }
    
    for original, replacement in party_mappings.items():
        parties = re.sub(rf'\b{original}\b', replacement, parties, flags=re.IGNORECASE)
    
    return parties

def normalize_judge(judge: str) -> str:
    """Normalize judge names"""
    if not judge:
        return judge
    
    # Remove extra whitespace
    judge = re.sub(r'\s+', ' ', judge.strip())
    
    # Standardize judge titles
    judge_mappings = {
        'chief justice': 'C.J.',
        'associate justice': 'J.',
        'judge': 'J.',
        'justice': 'J.'
    }
    
    for title, abbreviation in judge_mappings.items():
        judge = re.sub(rf'\b{title}\b', abbreviation, judge, flags=re.IGNORECASE)
    
    return judge

async def normalize_passage_citations(session, case_id: str):
    """Normalize citations found in passages"""
    
    # Get passages with citations
    passages_query = text("""
        SELECT id, content, metadata
        FROM passages 
        WHERE case_id = :case_id
    """)
    
    passages_result = session.execute(passages_query, {'case_id': case_id})
    passages = passages_result.fetchall()
    
    for passage in passages:
        # Extract citations from passage content
        citations = extract_citations_from_text(passage.content)
        
        if citations:
            # Normalize each citation
            normalized_citations = []
            for citation in citations:
                normalized_citation = citation_normalizer.normalize(citation)
                normalized_citations.append({
                    'original': citation,
                    'normalized': normalized_citation
                })
            
            # Update passage metadata with normalized citations
            metadata = passage.metadata or {}
            metadata['normalized_citations'] = normalized_citations
            
            update_query = text("""
                UPDATE passages 
                SET metadata = :metadata
                WHERE id = :passage_id
            """)
            
            session.execute(update_query, {
                'passage_id': passage.id,
                'metadata': json.dumps(metadata)
            })

def extract_citations_from_text(text: str) -> List[str]:
    """Extract legal citations from text"""
    # Common citation patterns
    citation_patterns = [
        # Standard case citations (e.g., "Smith v. Jones, 123 U.S. 456 (2020)")
        r'\b[A-Z][a-z]+ v\. [A-Z][a-z]+, \d+ [A-Z\.]+\s+\d+\s*\(\d{4}\)',
        # Short form citations (e.g., "Smith, 123 U.S. at 456")
        r'\b[A-Z][a-z]+, \d+ [A-Z\.]+ at \d+',
        # Statute citations (e.g., "42 U.S.C. § 1983")
        r'\d+ [A-Z\.]+ § \d+',
        # Regulation citations (e.g., "28 C.F.R. § 35.104")
        r'\d+ [A-Z\.]+ § \d+\.\d+'
    ]
    
    citations = []
    for pattern in citation_patterns:
        matches = re.findall(pattern, text)
        citations.extend(matches)
    
    return list(set(citations))  # Remove duplicates

async def publish_case_normalized(result: Dict[str, Any]):
    """Publish case normalized event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing case normalized event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "normalize-worker"}

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to case normalize events
    await nc.subscribe("case.normalize", cb=process_case_normalize)
    
    logger.info("Normalize worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
