import subprocess
import threading
from app.backend.logs.logger import logger
class StockfishSession:
    def __init__(self, path):
        self.process = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        self.lock = threading.Lock()

    def send(self, command: str):
        with self.lock:
            logger.debug("Sending to Stockfish: %s", command)
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def read_lines(self):
        while True:
            line = self.process.stdout.readline()
            if line:
                logger.debug("Raw Stockfish output: %s", line.strip())
                yield line.strip()