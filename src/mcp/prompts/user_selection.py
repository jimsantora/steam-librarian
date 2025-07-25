"""User selection prompt"""
from src.core.database import get_db
from src.models import UserProfile


def select_user_prompt() -> str:
    """Prompt to select which user to use for the query"""
    with get_db() as session:
        users = session.query(UserProfile).all()
        if not users:
            return "No users found in database. Please run the fetcher first with: python steam_library_fetcher.py"
        
        user_list = "\n".join([
            f"- {user.persona_name or 'Unknown'} (Steam ID: {user.steam_id})" 
            for user in users
        ])
    
    return f"""Please select a user for this query:

{user_list}

Enter the Steam ID of the user you want to use:"""