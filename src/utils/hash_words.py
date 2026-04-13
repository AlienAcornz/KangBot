import dbm
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # go from utils → src
DATA_PATH = BASE_DIR.parent / "data"
JSON_PATH = DATA_PATH / "banned_words.json"
DB_PATH = DATA_PATH / "hashed_banned_words"



def build_db(db_path: Path = DB_PATH, banned_words_path: Path = JSON_PATH) -> None:
    with open(banned_words_path, "r") as f: #Opens the json file as read only
        words = json.load(f)
    
    with dbm.open(db_path, "n") as db: #Creates a hash table of all the bad words
        for word in words:
            db[word] = "1" #This value is irrelevant. We only care about the key
    
    print(f"Stored {len(words)} banned words to '{db_path}'")


if __name__ == "__main__":
    build_db()
