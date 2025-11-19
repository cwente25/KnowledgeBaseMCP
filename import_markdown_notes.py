"""Import existing markdown notes into the database"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.config import settings
from api.database import Base
from api.models import Note as DBNote
from knowledge_base_mcp.storage import KnowledgeBaseStorage

def import_markdown_notes(user_id: str = None):
    """Import all markdown notes from knowledge base into database"""

    # Setup database
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Setup storage
    storage = KnowledgeBaseStorage(Path(settings.knowledge_base_path))

    # Get all existing notes from markdown files
    markdown_notes = storage.list_notes()

    imported = 0
    skipped = 0

    print(f"Found {len(markdown_notes)} markdown notes")
    print(f"Importing into database...")

    for md_note in markdown_notes:
        # Check if already in database
        existing = db.query(DBNote).filter(DBNote.file_path == str(md_note.file_path)).first()

        if existing:
            print(f"  [SKIP] Already exists: {md_note.title}")
            skipped += 1
            continue

        try:
            # Create database entry
            db_note = DBNote(
                title=md_note.title,
                content=md_note.content,
                category=md_note.category,
                tags=md_note.frontmatter.tags,
                note_metadata=md_note.frontmatter.metadata,
                file_path=str(md_note.file_path),
                user_id=user_id  # Associate with user if provided
            )
            db.add(db_note)
            db.commit()
            print(f"  [OK] Imported: {md_note.title} ({md_note.category})")
            imported += 1

        except Exception as e:
            db.rollback()
            print(f"  [ERROR] Failed to import {md_note.title}: {e}")

    db.close()

    print(f"\nImport complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {len(markdown_notes)}")

if __name__ == "__main__":
    # Get user ID from command line if provided
    user_id = sys.argv[1] if len(sys.argv) > 1 else None

    if user_id:
        print(f"Importing notes for user: {user_id}")
    else:
        print("Importing notes without user association")

    import_markdown_notes(user_id)
