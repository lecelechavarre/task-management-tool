import json
import os
from typing import List
from todo.models import Task

def load_tasks(filepath: str) -> List[Task]:
    """Load tasks from JSON file"""
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Use Task.from_dict which now properly loads completed_at
            return [Task.from_dict(item) for item in data]
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def save_tasks(filepath: str, tasks: List[Task]) -> None:
    """Save tasks to JSON file"""
    try:
        # Use task.to_dict() which uses asdict() and includes all fields including completed_at
        data = [task.to_dict() for task in tasks]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

def get_next_id(tasks: List[Task]) -> int:
    """Get the next available task ID"""
    if not tasks:
        return 1
    return max(task.id for task in tasks) + 1
