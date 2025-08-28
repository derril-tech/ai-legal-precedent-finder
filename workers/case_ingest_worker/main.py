"""
Case Ingest Worker - Main Entry Point

Handles case document ingestion from various sources:
- CourtListener API
- Caselaw Access Project
- Direct file uploads
- OCR processing for scanned documents
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import json
import uuid
from datetime import datetime

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .parser import CaseParser
from .ocr import OCRProcessor
from .models import CaseDocument, ParsedCase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for health checks and manual triggers
app = FastAPI(title="Case Ingest Worker", version="0.1.0")

# Configuration
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/legal_precedent_finder"
NATS_URL = "nats://nats:4222"
S3_ENDPOINT = "http://minio:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"

# Initialize components
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

case_parser = CaseParser()
ocr_processor = OCRProcessor()

class IngestRequest(BaseModel):
    """Request model for manual case ingestion"""
    source_url: Optional[str] = None
    file_content: Optional[str] = None
    file_type: str  # 'xml', 'html', 'pdf'
    workspace_id: str
    metadata: Dict[str, Any] = {}

class IngestResponse(BaseModel):
    """Response model for ingestion results"""
    case_id: str
    status: str
    message: str
    citations_found: int
    passages_created: int

async def process_case_ingest(msg: Msg):
    """Process case ingestion message from NATS"""
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Processing case ingest: {data.get('case_id', 'unknown')}")
        
        # Extract message data
        case_id = data.get('case_id')
        source_url = data.get('source_url')
        file_content = data.get('file_content')
        file_type = data.get('file_type', 'xml')
        workspace_id = data.get('workspace_id')
        metadata = data.get('metadata', {})
        
        # Process the case
        result = await ingest_case(
            case_id=case_id,
            source_url=source_url,
            file_content=file_content,
            file_type=file_type,
            workspace_id=workspace_id,
            metadata=metadata
        )
        
        # Publish completion event
        await publish_case_processed(result)
        
        # Acknowledge message
        await msg.ack()
        
    except Exception as e:
        logger.error(f"Error processing case ingest: {e}")
        await msg.nak()

async def ingest_case(
    case_id: str,
    source_url: Optional[str] = None,
    file_content: Optional[str] = None,
    file_type: str = 'xml',
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main case ingestion logic
    
    Args:
        case_id: Unique identifier for the case
        source_url: URL to fetch case document from
        file_content: Raw file content if available
        file_type: Type of document ('xml', 'html', 'pdf')
        workspace_id: Workspace to associate case with
        metadata: Additional metadata
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Get or create case document
        if file_content:
            document = CaseDocument(
                content=file_content,
                file_type=file_type,
                metadata=metadata or {}
            )
        elif source_url:
            document = await fetch_document_from_url(source_url, file_type)
        else:
            raise ValueError("Either file_content or source_url must be provided")
        
        # Parse the document
        parsed_case = await parse_document(document)
        
        # Store in database
        db_result = await store_case_in_database(
            case_id=case_id,
            parsed_case=parsed_case,
            workspace_id=workspace_id
        )
        
        # Store original document in S3
        s3_key = await store_document_in_s3(case_id, document)
        
        # Update database with S3 keys
        await update_case_s3_keys(case_id, s3_key)
        
        # Publish events for downstream processing
        await publish_normalization_event(case_id)
        await publish_embedding_event(case_id)
        
        return {
            'case_id': case_id,
            'status': 'success',
            'citations_found': len(parsed_case.citations),
            'passages_created': len(parsed_case.passages),
            's3_key': s3_key
        }
        
    except Exception as e:
        logger.error(f"Error ingesting case {case_id}: {e}")
        return {
            'case_id': case_id,
            'status': 'error',
            'error': str(e)
        }

async def fetch_document_from_url(url: str, file_type: str) -> CaseDocument:
    """Fetch document content from URL"""
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        return CaseDocument(
            content=response.text,
            file_type=file_type,
            metadata={'source_url': url}
        )

async def parse_document(document: CaseDocument) -> ParsedCase:
    """Parse document content into structured case data"""
    
    # Try OCR if needed
    if document.file_type == 'pdf' and not document.content.strip():
        document.content = await ocr_processor.extract_text(document.raw_content)
    
    # Parse based on file type
    if document.file_type == 'xml':
        return await case_parser.parse_xml(document.content)
    elif document.file_type == 'html':
        return await case_parser.parse_html(document.content)
    elif document.file_type == 'pdf':
        return await case_parser.parse_pdf(document.content)
    else:
        raise ValueError(f"Unsupported file type: {document.file_type}")

async def store_case_in_database(
    case_id: str,
    parsed_case: ParsedCase,
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """Store parsed case data in database"""
    
    with SessionLocal() as session:
        try:
            # Insert case record
            case_query = text("""
                INSERT INTO cases (
                    id, workspace_id, citation, docket_number, court, jurisdiction,
                    case_name, parties, outcome, decision_date, opinion_date,
                    judge, text_content, metadata
                ) VALUES (
                    :case_id, :workspace_id, :citation, :docket_number, :court, :jurisdiction,
                    :case_name, :parties, :outcome, :decision_date, :opinion_date,
                    :judge, :text_content, :metadata
                ) ON CONFLICT (citation) DO UPDATE SET
                    updated_at = NOW()
                RETURNING id
            """)
            
            case_result = session.execute(case_query, {
                'case_id': case_id,
                'workspace_id': workspace_id,
                'citation': parsed_case.citation,
                'docket_number': parsed_case.docket_number,
                'court': parsed_case.court,
                'jurisdiction': parsed_case.jurisdiction,
                'case_name': parsed_case.case_name,
                'parties': parsed_case.parties,
                'outcome': parsed_case.outcome,
                'decision_date': parsed_case.decision_date,
                'opinion_date': parsed_case.opinion_date,
                'judge': parsed_case.judge,
                'text_content': parsed_case.full_text,
                'metadata': parsed_case.metadata
            })
            
            # Insert passages
            for i, passage in enumerate(parsed_case.passages):
                passage_query = text("""
                    INSERT INTO passages (
                        case_id, passage_number, section_type, content, metadata
                    ) VALUES (
                        :case_id, :passage_number, :section_type, :content, :metadata
                    ) ON CONFLICT (case_id, passage_number) DO UPDATE SET
                        content = EXCLUDED.content,
                        section_type = EXCLUDED.section_type,
                        metadata = EXCLUDED.metadata
                """)
                
                session.execute(passage_query, {
                    'case_id': case_id,
                    'passage_number': i + 1,
                    'section_type': passage.section_type,
                    'content': passage.content,
                    'metadata': passage.metadata
                })
            
            session.commit()
            
            return {
                'case_id': case_id,
                'passages_created': len(parsed_case.passages)
            }
            
        except Exception as e:
            session.rollback()
            raise e

async def store_document_in_s3(case_id: str, document: CaseDocument) -> str:
    """Store original document in S3"""
    
    bucket_name = "legal-cases"
    s3_key = f"cases/{case_id}/original.{document.file_type}"
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=document.raw_content,
            ContentType=f"application/{document.file_type}"
        )
        return s3_key
    except Exception as e:
        logger.error(f"Error storing document in S3: {e}")
        raise e

async def update_case_s3_keys(case_id: str, s3_key: str):
    """Update case record with S3 keys"""
    
    with SessionLocal() as session:
        try:
            update_query = text("""
                UPDATE cases 
                SET s3_text_key = :s3_key
                WHERE id = :case_id
            """)
            
            session.execute(update_query, {
                'case_id': case_id,
                's3_key': s3_key
            })
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e

async def publish_normalization_event(case_id: str):
    """Publish event for case normalization"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing normalization event for case {case_id}")

async def publish_embedding_event(case_id: str):
    """Publish event for case embedding"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing embedding event for case {case_id}")

async def publish_case_processed(result: Dict[str, Any]):
    """Publish case processed event"""
    # This will be implemented when NATS client is available
    logger.info(f"Publishing case processed event: {result}")

# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "case-ingest-worker"}

@app.post("/ingest", response_model=IngestResponse)
async def manual_ingest(request: IngestRequest):
    """Manual case ingestion endpoint"""
    
    case_id = str(uuid.uuid4())
    
    result = await ingest_case(
        case_id=case_id,
        source_url=request.source_url,
        file_content=request.file_content,
        file_type=request.file_type,
        workspace_id=request.workspace_id,
        metadata=request.metadata
    )
    
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['error'])
    
    return IngestResponse(
        case_id=result['case_id'],
        status=result['status'],
        message="Case ingested successfully",
        citations_found=result.get('citations_found', 0),
        passages_created=result.get('passages_created', 0)
    )

async def main():
    """Main entry point"""
    
    # Connect to NATS
    nc = NATS()
    await nc.connect(NATS_URL)
    
    # Subscribe to case ingest events
    await nc.subscribe("case.ingest", cb=process_case_ingest)
    
    logger.info("Case ingest worker started and listening for events")
    
    # Keep the worker running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
