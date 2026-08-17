# Guache Digital

Web + bot conversacional de **Guache, C.A.**, agroindustria venezolana. Backend en FastAPI, bot de Telegram y asistente virtual "Guache" impulsado por LLM (Groq).

En producción: https://guache.online

## Documentación

- [`docs/EMPRESA.md`](docs/EMPRESA.md) — Perfil corporativo: quiénes somos, líneas de negocio, estrategia de expansión.
- [`docs/PROYECTO_TECNICO.md`](docs/PROYECTO_TECNICO.md) — Estado técnico del proyecto, arquitectura, cómo levantarlo en local y roadmap para nuevos desarrolladores.

## Quickstart

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # completar TELEGRAM_BOT_TOKEN y GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

Más detalle en [`docs/PROYECTO_TECNICO.md`](docs/PROYECTO_TECNICO.md).
