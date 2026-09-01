import sys
sys.path.append('.')
from main import get_synonyms

print("Testing Spanish:")
print(get_synonyms("perro", "es"))
