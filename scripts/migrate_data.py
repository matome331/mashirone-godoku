from core.database import DatabaseManager
import json
import os

def migrate():
    db = DatabaseManager()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'webapp', 'data.json')
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Migrating {len(data)} items...")
    
    for item in data:
        video_url = item.get('url', '')
        if not video_url: continue
        
        video_id = video_url.split('=')[-1]
        if '&' in video_id:
            video_id = video_id.split('&')[0]
        if 't=' in video_id:
            video_id = video_id.split('t=')[0].rstrip('?')
            
        db.add_video(video_id, item.get('video', 'Untitled'), video_url, item.get('date', ''))
        db.add_misreading(
            video_id=video_id,
            timestamp=item.get('timestamp_str', '0:00'),
            original=item.get('original', ''),
            reading=item.get('reading', ''),
            context=item.get('context', ''),
            status=1 # Automatically approved
        )
    
    print("Migration successful!")

if __name__ == "__main__":
    migrate()
