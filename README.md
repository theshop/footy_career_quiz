# Football Career Quiz

Guess the footballer from their career path!  
Type in any professional football (soccer) player’s name and the app will fetch that player’s Wikipedia page, hide the name, and present their club and international career. Hand the screen to a friend and see if they can identify the player only from the career timeline.

---

## ✨  Project Purpose
Football fans love testing each other’s knowledge. This lightweight web game turns every Wikipedia page into a trivia question:

1. Enter a player’s name.  
2. The app searches Wikipedia, grabs the player’s infobox & career section.  
3. All occurrences of the player’s name are masked.  
4. A clean “mystery résumé” is shown for your friend to guess.  
5. Reveal the answer and see who’s the ultimate footy nerd!

---

## 🛠️  How It Works

1. **Search & Fetch**  
   `wikipedia` API is queried for the exact player page (with a fallback search).  

2. **Parse**  
   The HTML is parsed with **BeautifulSoup** to extract:
   - Full club history
   - National team caps/goals
   - Position, birth year, height (optional)

3. **Obscure**  
   The player’s full name (and common short names) are replaced by █████ placeholders.

4. **Serve**  
   A small **Flask** (or **FastAPI**) backend exposes `/quiz?player=<name>`.  
   A minimal **React/Vite** (or plain HTML/JS) frontend renders the career table and provides “Show Answer” + “New Player” buttons.

---

## 🚀  Quick Start

### Prerequisites
- Python 3.10+  
- `pip`  
- (optional) `virtualenv` for an isolated environment

### Setup

```bash
# clone the repo
git clone https://github.com/theshop/footy_career_quiz.git
cd footy_career_quiz

# create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# install backend requirements
pip install -r requirements.txt

# run the server
python app.py
```

Navigate to `http://localhost:8000` (or the port shown in the console) and start playing!

---

## 🖼️  Example Screenshot
*(coming soon)*

---

## 📂  Project Structure (planned)

```
footy_career_quiz/
├─ app.py                 # Flask/FastAPI entrypoint
├─ core/
│   ├─ wiki.py            # search & retrieval logic
│   └─ parser.py          # HTML→career extraction
├─ frontend/              # static SPA or templates
│   └─ ...
├─ tests/
└─ requirements.txt
```

---

## 🧩  Roadmap

- [ ] Autocomplete suggestions while typing player names  
- [ ] Support multiple leagues/languages  
- [ ] Timed challenge & score tracking  
- [ ] Docker container for 1-command run  
- [ ] Deploy to Render / Fly.io

---

## 🤝  Contributing

Pull requests are welcome!  
1. Fork the repo  
2. Create a feature branch (`git checkout -b feat/my-feature`)  
3. Commit your changes with clear messages  
4. Run tests (`pytest`)  
5. Open a PR

---

## 📜  License
MIT
