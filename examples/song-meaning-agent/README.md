# 🎵 Song Meaning Analyzer

A Bindu agent that deeply researches songs, lyrics, artists, and cultural context
to uncover and articulate the true meaning behind any musical work.

## Features

- Accepts any song title, artist name, or pasted lyrics
- Produces structured analyses: SUMMARY, MEANING, and EVIDENCE
- Grounds every claim in lyrics, artist statements, or documented context
- Handles ambiguous songs by surfacing multiple interpretations
- Live A2A microservice via `bindufy()`

## Output Format

```text`r`nSUMMARY
A single sentence (25 words max) capturing the song's core meaning.

MEANING
- 3–5 bullets (~165 words each) covering themes, symbolism, and context

EVIDENCE
- 3–5 bullets (~15 words each) citing lyrics and artist statements
```

## Setup

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env

uv add bindu agno python-dotenv
python song_meaning_agent.py
```

The agent runs at `http://localhost:3773`.

## Example Queries

```json
{"role": "user", "content": "What does 'Bohemian Rhapsody' by Queen really mean?"}
{"role": "user", "content": "Analyze the deeper meaning behind these lyrics: ..."}
{"role": "user", "content": "Explain the themes and symbolism in this artist's work."}
{"role": "user", "content": "Uncover the meaning of 'The Sound of Silence' based on artist context."}
```

## Project Structure

```text`r`nsong-meaning-agent/
├── song_meaning_agent.py          # Main agent + bindufy()
├── .env.example                   # Environment variables
├── skills/
│   └── song-meaning-skill/
│       └── skill.yaml             # Skill definition
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `BINDU_DEPLOYMENT_URL` | No | Override default `http://localhost:3773` |


