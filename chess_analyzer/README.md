♟♟️ Chess Analyzer
A modular, production-grade chess analysis app built with FastAPI, Vue 3, and Stockfish. Supports FEN rendering, live analysis via WebSocket, PGN upload with session tracking, and SVG board visualization.

🚀 Features
• 	FEN Board Rendering: Send a FEN string and receive an SVG-rendered chess board.
• 	Live Stockfish Analysis: Stream multi-PV lines via WebSocket with throttled output.
• 	PGN Upload: Upload  files, store critical positions, and manage sessions.
• 	Modular Backend: Clean separation of routes, engine logic, and SVG rendering.
• 	Vue Frontend: Responsive UI with buttons for rendering, live analysis, and PGN upload.
• 	Persistent Stockfish Session: Keeps the engine warm for fast response times.
• 	SPA Routing Support: Vue Router history mode enabled via FastAPI fallback.


📦 Setup
1. Clone the repo
git clone https://github.com/your-org/chess-analyzer.git
cd chess-analyzer
2. Install backend dependencies
cd backend
pip install -r requirements.txt
3. Build the frontend
cd frontend
npm install
npm run build
4. Run the app
cd backend
python main.py
Visit: http://localhost:8000

🔌 API Endpoints
Absolutely, Dima — here’s the API Endpoints section rewritten in plain text for easy copy-pasting:

🔌 API Endpoints
POST /svg
Receives a FEN string in JSON and returns an SVG-rendered chess board.
Request body: 
Response: 

POST /analyze
Performs a one-shot Stockfish analysis on a given FEN.
Request body: 
Response: JSON with analysis lines

WebSocket /ws/analyze
Streams live multi-PV analysis from Stockfish.
Client sends: FEN string as plain text
Server responds: multiple lines of Stockfish output (e.g., )

POST /sessions
Creates a new PGN analysis session.
Request body: 
Response: 

POST /sessions/{session_id}/upload_pgn
Uploads a PGN file to an existing session.
Request:  with  field
Response: 


🧠 Dev Notes
• 	WebSocket stream throttled with 
• 	Vue frontend served via FastAPI static mount at 
• 	SPA fallback route handles Vue Router history mode
• 	PGN upload uses  and session-based routing
• 	Logging via custom 