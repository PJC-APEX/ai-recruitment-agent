# Resume Screening System - Frontend

Modern React chat-based UI for the Resume Screening and Matching System.

## Features

- **Chat Interface**: ChatGPT-style conversation interface
- **Resume Upload**: Drag-and-drop PDF upload
- **Candidate Display**: Real-time candidate cards with scores
- **Natural Language Queries**: Search and rank candidates conversationally
- **Responsive Design**: Modern, mobile-friendly UI with TailwindCSS

## Tech Stack

- **React 18**: Modern React with Hooks
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **React Dropzone**: Drag-and-drop file upload

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The application will be available at: http://localhost:5173

## Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatBox.jsx          # Chat message display
│   │   ├── MessageBubble.jsx    # Individual message
│   │   ├── ResumeUpload.jsx     # Drag-drop uploader
│   │   └── CandidateCard.jsx    # Candidate info card
│   ├── pages/
│   │   └── ChatPage.jsx         # Main chat page
│   ├── services/
│   │   └── api.js               # API client
│   ├── App.jsx                  # Root component
│   ├── main.jsx                 # Entry point
│   └── index.css                # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Usage

### Upload Resume

1. Click the "Upload Resume" button in the header
2. Drag and drop a PDF file or click to browse
3. Wait for confirmation message

### Search Candidates

Type natural language queries like:

- "Find candidates with 5 years of Python experience"
- "Who has .NET and SQL skills?"
- "Search for senior developers"

### View Results

- Matching candidates appear in the right panel
- Each card shows:
  - Candidate name
  - Relevance score
  - Skills
  - File name

## API Configuration

The frontend is configured to connect to the backend at `http://localhost:8000`.

To change the API URL, edit [src/services/api.js](src/services/api.js):

```javascript
const API_BASE_URL = 'http://your-backend-url/api';
```

## Components

### ChatBox

Displays the conversation history with auto-scroll and empty state.

### MessageBubble

Individual message component supporting:
- User vs AI styling
- Candidate data display
- Timestamps

### ResumeUpload

Drag-and-drop uploader with:
- File validation (PDF only, 10MB max)
- Progress indicator
- Success/error feedback

### CandidateCard

Displays candidate information:
- Name and filename
- Match/relevance score with color coding
- Skills (matching and missing)
- Experience
- Summary

### ChatPage

Main page component orchestrating:
- Chat interface
- Message handling
- Resume upload
- Candidate display

## Styling

The app uses TailwindCSS with a dark theme:

- **Primary Color**: Blue (customizable in tailwind.config.js)
- **Dark Background**: Gray-900
- **Cards**: Gray-800
- **Hover Effects**: Primary-500

## Development

### Run Linter

```bash
npm run lint
```

### Preview Production Build

```bash
npm run preview
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

MIT
