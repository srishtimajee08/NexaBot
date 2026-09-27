"""Production settings: one worker avoids duplicating the embedding model in RAM."""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 1
threads = 2
timeout = 120
accesslog = "-"
errorlog = "-"
