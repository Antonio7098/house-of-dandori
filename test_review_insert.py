from src.models.database import get_db_connection
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviews (user_id, course_id, rating, review) 
        VALUES ('dev_user', 83, 4, 'Pretty good!') 
        ON CONFLICT(user_id, course_id) DO UPDATE SET 
            rating = EXCLUDED.rating, 
            review = EXCLUDED.review, 
            created_at = CURRENT_TIMESTAMP
    """)
    conn.commit()
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
