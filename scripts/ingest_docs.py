#!/usr/bin/env python
# scripts/ingest_docs.py
"""
Production-ready script to ingest documents from the /datasets directory into the RAG knowledge base.

This script:
1. Scans a specified agent's dataset directory for .pdf, .md, and .html files.
2. Parses each file type to extract clean, readable text.
3. Chunks the text into overlapping segments suitable for embedding.
4. Uses the application's core RAG service to generate embeddings and ingest the data
   into the 'docs' table in PostgreSQL.

Usage:
    python scripts/ingest_docs.py <agent_name>
    (e.g., python scripts/ingest_docs.py support)

Requires the following libraries:
    pip install pypdf markdown-it-py beautifulsoup4
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

# --- Add service source to Python path for imports ---
# This allows the script to import modules from the api-gateway service
SERVICE_SRC_PATH = Path(__file__).parent.parent / "services" / "api-gateway" / "src"
sys.path.append(str(SERVICE_SRC_PATH))

# --- Dependency Imports ---
# These must be installed in the environment: pip install pypdf markdown-it-py beautifulsoup4
try:
    import pypdf
    from bs4 import BeautifulSoup
    from markdown_it import MarkdownIt
except ImportError as e:
    print(f"ImportError: {e}. Please install required libraries: pip install pypdf markdown-it-py beautifulsoup4")
    sys.exit(1)

# --- Application Imports ---
# This will fail if the path append above is incorrect
from runtime.rag import RAG

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


# --- File Parsers ---

def read_pdf(path: Path) -> str:
    """Extracts text content from a PDF file."""
    try:
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            return "\n".join(page.extract_text() for page in reader.pages)
    except Exception as e:
        logging.error(f"Failed to parse PDF {path}: {e}")
        return ""


def read_markdown(path: Path) -> str:
    """Extracts text from a Markdown file by rendering it to HTML first."""
    try:
        md_parser = MarkdownIt()
        with open(path, "r", encoding="utf-8") as f:
            html_content = md_parser.render(f.read())
            return BeautifulSoup(html_content, "html.parser").get_text()
    except Exception as e:
        logging.error(f"Failed to parse Markdown {path}: {e}")
        return ""


def read_html(path: Path) -> str:
    """Extracts text content from an HTML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f, "html.parser").get_text()
    except Exception as e:
        logging.error(f"Failed to parse HTML {path}: {e}")
        return ""


# --- Text Processing ---

def chunk_text(text: str) -> List[str]:
    """Splits text into overlapping chunks."""
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunks.append(chunk)
    return chunks


# --- Main Execution Logic ---

async def main() -> None:
    """Main function to orchestrate the ingestion process."""
    parser = argparse.ArgumentParser(description="Ingest documents into RAG for a specific agent.")
    parser.add_argument(
        "agent_name",
        type=str,
        help="The name of the agent whose dataset should be ingested (e.g., 'support')."
    )
    args = parser.parse_args()

    dataset_path = Path(__file__).parent.parent / "datasets" / args.agent_name
    if not dataset_path.is_dir():
        logging.error(f"Error: Directory not found for agent '{args.agent_name}' at '{dataset_path}'")
        return

    logging.info(f"Scanning for documents in: {dataset_path}")
    supported_files = list(dataset_path.rglob("*.pdf"))
    supported_files.extend(list(dataset_path.rglob("*.md")))
    supported_files.extend(list(dataset_path.rglob("*.html")))

    if not supported_files:
        logging.warning("No supported documents (.pdf, .md, .html) found.")
        return

    logging.info(f"Found {len(supported_files)} documents to process.")

    all_chunks: List[str] = []
    all_sources: List[str] = []

    parser_map = {
        ".pdf": read_pdf,
        ".md": read_markdown,
        ".html": read_html,
    }

    for file_path in supported_files:
        logging.info(f"  - Processing {file_path.name}...")
        parser = parser_map.get(file_path.suffix.lower())
        if not parser:
            continue

        text_content = parser(file_path)
        if text_content:
            chunks = chunk_text(text_content)
            all_chunks.extend(chunks)
            all_sources.extend([str(file_path)] * len(chunks))
            logging.info(f"    ...extracted {len(chunks)} chunks.")

    if not all_chunks:
        logging.error("No text could be extracted from any documents. Aborting.")
        return

    logging.info(f"Total chunks to ingest: {len(all_chunks)}")

    # --- Ingestion using RAG Service ---
    try:
        logging.info("Initializing RAG service...")
        rag_service = RAG()
        await rag_service.ainit()  # Initialize connections

        logging.info("Starting ingestion into database...")
        await rag_service.ingest_documents(documents=all_chunks, sources=all_sources)
        logging.info("Ingestion complete!")

    except Exception as e:
        logging.error(f"An error occurred during RAG initialization or ingestion: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure DATABASE_URL is set
    if "DATABASE_URL" not in os.environ:
        logging.error("FATAL: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    asyncio.run(main())