import os
import tempfile

def get_model_dir():
    """
    Determine the best writable directory to store the AI model.
    Tries paths in the following order:
    1. ECRITURE_MODEL_DIR environment variable
    2. XDG_CACHE_HOME/ecriture
    3. ~/.cache/ecriture
    4. os.getcwd()/ecriture_models
    5. tempfile.gettempdir()/ecriture
    """
    candidates = []

    # 1. Custom ENV var
    if "ECRITURE_MODEL_DIR" in os.environ:
        candidates.append(os.environ["ECRITURE_MODEL_DIR"])

    # 2. XDG_CACHE_HOME
    if "XDG_CACHE_HOME" in os.environ:
        candidates.append(os.path.join(os.environ["XDG_CACHE_HOME"], "ecriture"))

    # 3. Standard user cache
    candidates.append(os.path.join(os.path.expanduser("~"), ".cache", "ecriture"))

    # 4. Local working directory
    candidates.append(os.path.join(os.getcwd(), "ecriture_models"))

    # 5. OS Temp directory
    candidates.append(os.path.join(tempfile.gettempdir(), "ecriture"))

    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            # Test write permissions by creating and removing a dummy file
            test_file = os.path.join(d, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return d
        except Exception:
            pass

    # Fallback to temp dir without strict checks if everything else fails
    fallback = os.path.join(tempfile.gettempdir(), "ecriture")
    os.makedirs(fallback, exist_ok=True)
    return fallback
