♟️ Chess Analyzer
A modular chess analysis platform built with FastAPI (backend), Vue 3 (frontend), and Stockfish (engine).
It allows users to upload PGN files, extract critical positions, and test themselves interactively against engine‑evaluated lines.

🚀 Features
• 	PGN Upload: Upload a PGN file and automatically extract critical positions (with  markers).
• 	Dynamic Analysis: Run Stockfish analysis on critical positions with multiple candidate lines.
• 	TestMe Mode: Practice decision‑making on critical positions after PGN upload.
• 	Clean Architecture: Modular backend with async Postgres integration ( /  ready).
• 	Frontend UI: Vue‑based interface with  as the main component.

📂 Project Structure
chess_analyzer/
│
├── backend/                # FastAPI backend
│   ├── main.py              # Entry point (Uvicorn app)
│   ├── db/                  # Database layer
│   ├── engine/              # Stockfish integration
│   └── routes/              # API endpoints
│
├── frontend/               # Vue 3 frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── Analyzer.vue
│   │   └── main.js
│   └── public/
│       └── index.html
│
├── tests/                  # Async pytest suite
├── requirements.txt        # Python dependencies
└── README.md

⚙️ Backend Setup
1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
2. Install dependencies
pip install -r requirements.txt
3. Run backend
uvicorn chess_analyzer.backend.main:app --reload
Backend runs at: http://127.0.0.1:8000
   (see main.py)
🎨 Frontend Setup
1. Install dependencies
cd frontend
npm install
2. Run dev server
npm run dev
Frontend runs at: http://localhost:5173 (Vite default).

🗄️ Database
• 	Postgres with async driver ( / ).
• 	Schema includes:
• 	 (stores PGN + status)
• 	 (FENs extracted from PGN)
• 	 +  (engine results)

🧪 Testing
Run async tests with:
pytest -v

🤝 Contributing
1. 	Fork the repo
2. 	Create a feature branch ()
3. 	Commit changes ()
4. 	Push branch ()
5. 	Open a Pull Request

📜 License
MIT License — feel free to use, modify, and distribute.