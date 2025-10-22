#!/usr/bin/env python3
"""
Test script for the Knowledge Base MCP Server.
Demonstrates adding notes, searching, and updating them.
"""

import tempfile
import shutil
from pathlib import Path
from src.knowledge_base_mcp.storage import KnowledgeBaseStorage
from src.knowledge_base_mcp.search import KnowledgeBaseSearch


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def main():
    # Create a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix="kb_test_"))
    print(f"\n🗂️  Test knowledge base location: {test_dir}\n")

    try:
        # Initialize storage and search
        categories = ["people", "recipes", "meetings", "procedures", "tasks"]
        storage = KnowledgeBaseStorage(str(test_dir), categories)
        search_engine = KnowledgeBaseSearch(storage)

        # =====================================================================
        # SECTION 1: Creating Notes
        # =====================================================================
        print_section("1. CREATING NOTES")

        # Create a person note
        print("\n📝 Creating note: 'Sarah Chen' in people/")
        note1 = storage.create_note(
            category="people",
            title="Sarah Chen",
            content="""**Met:** Tech Conference 2025, Silicon Valley
**Contact:** sarah.chen@tesla.com

## Background

Sarah is a battery engineer at Tesla working on next-generation battery technology.
She has extensive experience in lithium-ion optimization and thermal management.

## Discussion

- Interested in our AI product for battery optimization
- Has budget approval for Q1 2026
- Working on a project to reduce charging time by 40%

## Follow-up

- [ ] Send demo link by end of week
- [ ] Schedule call for next Tuesday
- [ ] Share case studies from automotive sector""",
            tags=["conference", "tesla", "important", "batteries"],
            metadata={"company": "Tesla", "role": "Battery Engineer", "email": "sarah.chen@tesla.com"}
        )
        print(f"✓ Created: {note1.title}")
        print(f"  File: {storage.sanitize_filename(note1.title)}.md")
        print(f"  Tags: {', '.join(note1.frontmatter.tags)}")

        # Create another person note
        print("\n📝 Creating note: 'John Martinez' in people/")
        note2 = storage.create_note(
            category="people",
            title="John Martinez",
            content="""**Met:** Weekly team sync
**Contact:** john.m@acme.com

## Background

John is the VP of Engineering at Acme Corp. Former Google engineer with 15 years experience.

## Notes

- Looking for automation solutions
- Team of 50 engineers
- Planning major infrastructure upgrade in Q2

## Action Items

- [ ] Share pricing information
- [ ] Arrange demo with their team""",
            tags=["team-sync", "acme", "automation"],
            metadata={"company": "Acme Corp", "role": "VP Engineering", "email": "john.m@acme.com"}
        )
        print(f"✓ Created: {note2.title}")
        print(f"  Tags: {', '.join(note2.frontmatter.tags)}")

        # Create a recipe note
        print("\n📝 Creating note: 'Brussels Sprouts' in recipes/")
        note3 = storage.create_note(
            category="recipes",
            title="Brussels Sprouts",
            content="""## Ingredients

- 1 lb Brussels sprouts, halved
- 2 tbsp olive oil
- Salt and pepper to taste
- Optional: balsamic glaze

## Instructions

1. Preheat air fryer to 400°F
2. Toss Brussels sprouts with olive oil, salt, and pepper
3. Place in air fryer basket in a single layer
4. Cook for 15-18 minutes, shaking basket halfway through
5. Sprouts should be crispy and golden brown
6. Optional: drizzle with balsamic glaze before serving

## Notes

- Works great as a side dish
- Can add parmesan cheese in the last 2 minutes
- Adjust time based on size of sprouts""",
            tags=["quick", "vegetables", "air-fryer", "healthy"],
            metadata={"prep_time": "5 min", "cook_time": "18 min", "servings": "4"}
        )
        print(f"✓ Created: {note3.title}")
        print(f"  Tags: {', '.join(note3.frontmatter.tags)}")

        # Create a task note
        print("\n📝 Creating note: 'Q4 Launch Preparation' in tasks/")
        note4 = storage.create_note(
            category="tasks",
            title="Q4 Launch Preparation",
            content="""## Product Launch Checklist

### Pre-Launch (3 weeks out)
- [ ] Finalize feature set
- [ ] Complete QA testing
- [ ] Prepare marketing materials
- [ ] Set up analytics tracking

### Launch Week
- [ ] Deploy to production
- [ ] Monitor performance metrics
- [ ] Coordinate with support team
- [ ] Social media announcements

### Post-Launch
- [ ] Collect user feedback
- [ ] Address critical bugs
- [ ] Plan iteration roadmap

## Key Dates

- Beta testing: Oct 15
- Launch date: Nov 1
- Retrospective: Nov 8""",
            tags=["launch", "q4", "high-priority", "product"],
            metadata={"priority": "high", "due_date": "2025-11-01", "status": "in-progress"}
        )
        print(f"✓ Created: {note4.title}")
        print(f"  Tags: {', '.join(note4.frontmatter.tags)}")

        # =====================================================================
        # SECTION 2: Listing Notes
        # =====================================================================
        print_section("2. LISTING ALL NOTES")

        all_notes = storage.list_notes()
        print(f"\n📚 Total notes: {len(all_notes)}\n")

        # Get category stats
        stats = storage.get_category_stats()
        for category, count in sorted(stats.items()):
            if count > 0:
                plural = "note" if count == 1 else "notes"
                print(f"  {category}/: {count} {plural}")

                # List notes in this category
                cat_notes = storage.list_notes(category=category)
                for note in sorted(cat_notes, key=lambda n: n.title):
                    tags_str = ', '.join(note.frontmatter.tags) if note.frontmatter.tags else 'no tags'
                    print(f"    - {note.title} [{tags_str}]")

        # =====================================================================
        # SECTION 3: Searching Notes
        # =====================================================================
        print_section("3. SEARCHING NOTES")

        # Search by content
        print("\n🔍 Search: 'battery' (full-text search)")
        results = search_engine.search(query="battery")
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ [{note.category}] {note.title} (score: {result.relevance_score:.1f})")
                print(f"    Tags: {', '.join(note.frontmatter.tags)}")
        else:
            print("  No results found")

        # Search by category
        print("\n🔍 Search: category='recipes'")
        results = search_engine.search(category="recipes")
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ [{note.category}] {note.title}")
                print(f"    Tags: {', '.join(note.frontmatter.tags)}")
        else:
            print("  No results found")

        # Search by tag
        print("\n🔍 Search: tags=['important']")
        results = search_engine.search(tags=["important"])
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ [{note.category}] {note.title}")
                print(f"    Tags: {', '.join(note.frontmatter.tags)}")
        else:
            print("  No results found")

        # Combined search
        print("\n🔍 Search: query='engineer' in category='people'")
        results = search_engine.search(query="engineer", category="people")
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ [{note.category}] {note.title} (score: {result.relevance_score:.1f})")
                print(f"    Tags: {', '.join(note.frontmatter.tags)}")
                if note.frontmatter.metadata:
                    if 'role' in note.frontmatter.metadata:
                        print(f"    Role: {note.frontmatter.metadata['role']}")
        else:
            print("  No results found")

        # =====================================================================
        # SECTION 4: Retrieving a Note
        # =====================================================================
        print_section("4. RETRIEVING A SPECIFIC NOTE")

        print("\n📖 Getting note: 'Sarah Chen' from people/")
        retrieved_note = storage.get_note("people", "Sarah Chen")
        print(f"\nTitle: {retrieved_note.title}")
        print(f"Category: {retrieved_note.category}")
        print(f"Tags: {', '.join(retrieved_note.frontmatter.tags)}")
        print(f"Created: {retrieved_note.frontmatter.date}")
        if retrieved_note.frontmatter.metadata:
            print(f"Metadata:")
            for key, value in retrieved_note.frontmatter.metadata.items():
                print(f"  - {key}: {value}")
        print(f"\nContent preview:\n{retrieved_note.content[:200]}...")

        # =====================================================================
        # SECTION 5: Updating Notes
        # =====================================================================
        print_section("5. UPDATING NOTES")

        # Append to existing note
        print("\n✏️  Appending to 'Sarah Chen' note")
        updated_note = storage.update_note(
            category="people",
            title="Sarah Chen",
            content="""## Meeting Update (October 22)

Had a great call with Sarah today:
- She loved the demo
- Wants to pilot with her team in November
- Needs integration with their existing battery management system
- Will introduce us to her director next week""",
            append=True
        )
        print(f"✓ Updated: {updated_note.title}")
        print(f"  Last updated: {updated_note.frontmatter.updated}")

        # Update tags
        print("\n✏️  Updating tags for 'Q4 Launch Preparation'")
        updated_note2 = storage.update_note(
            category="tasks",
            title="Q4 Launch Preparation",
            tags=["launch", "q4", "high-priority", "product", "urgent"]
        )
        print(f"✓ Updated: {updated_note2.title}")
        print(f"  New tags: {', '.join(updated_note2.frontmatter.tags)}")

        # Replace content
        print("\n✏️  Replacing content for 'Brussels Sprouts'")
        updated_note3 = storage.update_note(
            category="recipes",
            title="Brussels Sprouts",
            content="""## Ingredients

- 1 lb Brussels sprouts, halved
- 2 tbsp olive oil
- 2 cloves garlic, minced
- Salt and pepper to taste
- 2 tbsp balsamic glaze
- 1/4 cup parmesan cheese, grated

## Instructions

1. Preheat air fryer to 400°F
2. Toss Brussels sprouts with olive oil, garlic, salt, and pepper
3. Place in air fryer basket in a single layer
4. Cook for 15-18 minutes, shaking basket halfway through
5. In the last 2 minutes, sprinkle with parmesan cheese
6. Drizzle with balsamic glaze before serving

## Notes

- Updated recipe with garlic and parmesan - much better!
- Tried with different seasonings - garlic is key
- Makes a great side for grilled chicken""",
            append=False
        )
        print(f"✓ Updated: {updated_note3.title}")
        print(f"  Content replaced with improved recipe")

        # =====================================================================
        # SECTION 6: Final Search to Verify Updates
        # =====================================================================
        print_section("6. VERIFYING UPDATES")

        print("\n🔍 Search for 'pilot' to find updated content")
        results = search_engine.search(query="pilot")
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ Found in [{note.category}] {note.title}")
                print(f"    (Content was successfully appended)")
        else:
            print("  No results found")

        print("\n🔍 Search for 'urgent' tag")
        results = search_engine.search(tags=["urgent"])
        if results:
            for result in results:
                note = result.note
                print(f"  ✓ Found [{note.category}] {note.title}")
                print(f"    Tags: {', '.join(note.frontmatter.tags)}")
        else:
            print("  No results found")

        # =====================================================================
        # Summary
        # =====================================================================
        print_section("SUMMARY")

        print(f"""
✅ Test completed successfully!

Created notes:
  - 2 person notes (Sarah Chen, John Martinez)
  - 1 recipe note (Brussels Sprouts)
  - 1 task note (Q4 Launch Preparation)

Performed operations:
  ✓ Created 4 notes across different categories
  ✓ Listed all notes with category breakdown
  ✓ Searched by content, category, and tags
  ✓ Retrieved specific notes
  ✓ Appended content to existing note
  ✓ Updated tags
  ✓ Replaced content

Knowledge base location: {test_dir}
All markdown files are ready to view!
        """)

        # Return the test directory path for showing files
        return test_dir

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_dir = main()
    if test_dir:
        print(f"\n💡 To view the markdown files, check: {test_dir}")
