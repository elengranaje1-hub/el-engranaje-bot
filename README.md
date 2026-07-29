# El Engranaje — bot de producción automática

Canal de video-ensayo de crítica social en español, formato Shorts/TikTok.
Pipeline 100% automatizado con GitHub Actions. Costo de infraestructura: $0-5/mes.

## Arquitectura

```
guion (Groq)  →  arte (Pollinations/Flux)  →  voz (edge-tts)
                                                    │
                        composición (Pillow + ffmpeg, frame a frame)
                                                    │
                              subida (YouTube Data API)
```

## Estructura

- `scripts/` — motor del pipeline
- `fonts/` — Anton (tipografía de los carteles)
- `assets/style_refs/` — imágenes de referencia del estilo visual fijo
- `config/` — prompt maestro de guion y de arte
- `.github/workflows/` — cron que dispara la producción

## Estado

🚧 En construcción — fase 1: esqueleto y motor de composición.
