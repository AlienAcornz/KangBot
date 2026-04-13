import unicodedata
import re
import string
import dbm
from pathlib import Path
from hash_words import DB_PATH

def contains_bad_word(message: str, db_path: Path = DB_PATH) -> list[str]:
    words = message.lower().split() #Splits the sentence up into words
    found: list[str] = [] #creates a list of all bad words
    with dbm.open(db_path, "r") as db:
        for word in words:
            clean = word.strip(".,?:'-#\"")
            if clean in db: #checks the hash table for the bad words
                found.append(clean)
    return found #returns the list of bad words. Returns [] if there are none

def normalize_message(text: str) -> str:

    text = unicodedata.normalize("NFKD", text) # convert unicode characters such as ₣ to F
    text = text.encode("ascii", "ignore").decode("ascii") #convert text to ASCII

    text = text.lower()

    #Replace common problematic characters
    replacements = {
        "\n": " ",
        "\r": " ",
        "\t": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    allowed_punctuation = set(".,!?'-\"#$£%*")  # keep minimal useful punctuation
    allowed_chars = set(string.ascii_lowercase + string.digits).union(allowed_punctuation)

    # remove unwanted characters
    text = "".join(char if char in allowed_chars else " " for char in text)

    # collapse multiple punctuation
    text = re.sub(r'([.,!?\'-\"#$£%*])\1+', r'\1', text)

    # remove spaces before punctuation
    text = re.sub(r'\s+([.,!?])', r'\1', text)

    # ensure space after punctuation
    text = re.sub(r'([.,!?])([^\s])', r'\1 \2', text)

    # collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # strip leading/trailing whitespace
    text = text.strip()

    return text

