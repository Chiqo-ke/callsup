# CALLSUP Web Dashboard

React 19 + TypeScript + Vite frontend for the CALLSUP call-support platform.

## Pages

| Page | Route key | Purpose |
|------|-----------|---------|
| Dashboard | `dashboard` | Live service health, call-support analytics, escalation task queue |
| Audio Ingest | `ingest` | Upload audio files for transcription |
| Transcripts | `transcripts` | Browse and search conversation transcripts |
| Intelligence | `intelligence` | Step-by-step intelligence analysis (raises escalation tickets on `escalate: true`) |
| Context | `context` | Manage business context items used by the intelligence engine |
| Simulation | `simulation` | Simulate a call conversation (raises escalation tickets on `escalate: true`) |

## Dashboard Features

- **Stats row**: Tickets Pending (amber), Resolved Today (emerald), Total Escalations, Services Online (X/3)
- **Service health cards**: Name, status badge (online/offline/loading), and version — no raw URLs exposed
- **Task Queue**: Table of escalated tickets requiring human intervention. Each row shows conversation ID, reason, timestamp, status badge, and a Resolve button

## Escalation Ticket System

When the Intelligence Engine or Call Simulation determines a conversation needs human intervention (`escalate: true`), a ticket is automatically created and appears in the Dashboard task queue.

Tickets are persisted in `localStorage` under the key `callsup_tickets`. Resolving a ticket in the dashboard marks it as `"resolved"` and updates the stats counters.

```typescript
interface EscalatedTicket {
  id: string;          // nanoid
  conv_id: string;
  business_id: string;
  reason: string;
  timestamp: string;   // ISO 8601
  status: "pending" | "resolved";
}
```

## Backend Services

| Service | Port | Purpose |
|---------|------|---------|
| Audio Engine | 8010 | Whisper-based transcription |
| Intelligence Engine | 8011 | NLU, intent detection, action decisions |
| LLM Adapter | 9100 | GitHub Copilot / OpenAI proxy with redaction |

> Service URLs are internal only — they are not displayed in the UI.

## Development

```powershell
Set-Location "C:\Users\nyaga\Documents\callsup\callsup-web"
npm install
npm run dev          # starts at http://localhost:5173
```

## Build

```powershell
npm run build        # output to dist/
```

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
