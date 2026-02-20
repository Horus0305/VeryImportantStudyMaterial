"""
Database Migration Script for CPU Learning Infrastructure
Run this script to create all CPU learning tables.
"""
from sqlalchemy import create_engine, inspect
from .core.config import DATABASE_URL
from .cpu.cpu_learning_schema import Base as LearningBase
from .data.database import Base as MainBase


def migrate_cpu_learning_tables():
    """Create all CPU learning tables if they don't exist."""
    print("🔧 Starting CPU Learning Infrastructure Migration...")
    
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Tables to create
    learning_tables = [
        'match_ball_log',
        'cpu_global_patterns',
        'cpu_user_profiles',
        'cpu_situational_patterns',
        'cpu_sequence_patterns',
        'cpu_learning_progress',
        'cpu_learning_queue'
    ]
    
    # Create all tables
    print("\n📊 Creating CPU Learning Tables...")
    LearningBase.metadata.create_all(bind=engine)
    
    # Verify creation
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    
    print("\n✅ Migration Complete!")
    print("\nCreated Tables:")
    for table in learning_tables:
        if table in new_tables:
            print(f"  ✓ {table}")
            
            # Show indices for this table
            indices = inspector.get_indexes(table)
            if indices:
                print(f"    Indices: {len(indices)}")
                for idx in indices:
                    cols = ', '.join(idx['column_names'])
                    print(f"      - {idx['name']}: ({cols})")
        else:
            print(f"  ✗ {table} - FAILED")
    
    print("\n📈 Database Schema Summary:")
    print(f"  Total tables: {len(new_tables)}")
    print(f"  Learning tables: {sum(1 for t in learning_tables if t in new_tables)}")
    
    print("\n🎯 Next Steps:")
    print("  1. Restart your FastAPI server")
    print("  2. Play matches - data will be collected automatically")
    print("  3. Check cpu_learning_queue table to verify processing")
    print("  4. Monitor cpu_learning_progress to see user learning phases")
    
    return True


if __name__ == "__main__":
    try:
        migrate_cpu_learning_tables()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
