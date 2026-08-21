# AQG Studio - Frontend Application

## Overview
This directory contains the Next.js 15 (App Router) frontend application for AQG Studio, written in TypeScript and styled with Tailwind CSS.

## Key Modules (Phase 12 Delivery Target)
- **Document Ingestion Hub**: Drag-and-drop file upload with format validation, upload progress indicators, and extracted content viewer.
- **Assessment Blueprint Builder**: Interactive matrix for configuring target question quotas, difficulty ratios, and Bloom’s Taxonomy cognitive depth sliders.
- **Live Generation Streamer**: Server-Sent Events (SSE) listener rendering real-time progress as the 6 LangGraph backend agents execute.
- **Human Review Studio**: Side-by-side question editor, distractor tuner, rubric inspector, and verbatim source citation highlighter.
- **Export Center**: Instant download center for PDF, DOCX, Moodle XML, GIFT, QTI 2.1, JSON, and CSV.

## Development Scripts
- `npm run dev`: Start Next.js development server at `http://localhost:3000`
- `npm run build`: Compile production-ready bundle
- `npm run lint`: Run ESLint checks
- `npm run typecheck`: Run TypeScript static type checking
- `npm test`: Run frontend unit and component tests
