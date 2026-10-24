# StormReady React Frontend

Modern React/Next.js frontend for the StormReady AI Outage Concierge with Ohio State branding.

## Features

- **CometDial Component**: Beautiful circular sliders for crew availability
- **Ohio State Colors**: Scarlet (#BB0000), Grey, and White color scheme
- **Real-time Updates**: Connects to Python FastAPI backend
- **Responsive Design**: Works on desktop and mobile
- **Accessible**: WCAG compliant with keyboard navigation

## Prerequisites

- Node.js 18+ and npm/yarn
- Python backend running on port 8000

## Installation

```bash
cd frontend
npm install
# or
yarn install
```

## Development

1. **Start the Python backend** (from project root):
   ```bash
   pip install -r requirements.txt
   python api_server.py
   ```

2. **Start the React frontend**:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000)

## Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Main page
│   │   └── globals.css   # Global styles
│   ├── components/       # React components
│   │   ├── CometDial.tsx # Circular dial component
│   │   └── CometDial.css # Dial styles
│   └── lib/              # Utilities
│       └── api.ts        # API client
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## API Configuration

The frontend expects the backend API at `http://localhost:8000` by default.

To change this, set the environment variable:

```bash
NEXT_PUBLIC_API_URL=http://your-api-url:port npm run dev
```

## Ohio State Branding

Colors are defined in `tailwind.config.js`:
- **Scarlet**: #BB0000 (primary)
- **Grey**: #666666 (secondary)
- **Light**: #F5F5F5 (background)
- **Dark**: #2C2C2C (text)

## Components

### CometDial

Circular dial component from React Bits with Ohio State styling:

```tsx
<CometDial
  value={4}
  min={1}
  max={10}
  step={1}
  unit=" crews"
  label="Available Crews"
  accent="#BB0000"
  ink="#666666"
  size={200}
  onChange={(value) => console.log(value)}
/>
```

## Deployment

### Vercel (Recommended)

```bash
npm run build
vercel deploy
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Troubleshooting

**Backend Connection Issues**:
- Ensure Python API is running: `python api_server.py`
- Check CORS settings in `api_server.py`
- Verify API URL in frontend

**Build Errors**:
- Clear `.next` folder: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`

## License

Built for AEP HackOHIO 2026
