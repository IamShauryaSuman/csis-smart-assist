# CSIS SmartAssist - Frontend Design System & Architecture

## 1. Project Context & Philosophy

- [cite_start]**Project Name:** CSIS SmartAssist[cite: 1].
- [cite_start]**Goal:** A secure, web-based conversational assistant with smart resource booking[cite: 9, 11].
- [cite_start]**Constraint:** Optimized for a 24-hour hackathon build[cite: 36]. [cite_start]The UI skeleton must be deployable within Hour 0-3.
- **Vibe:** Utilitarian, dark-mode first, brutalist, and "computer-sciency." Focus on high information density and structural clarity over heavy animations.
- [cite_start]**Tech Stack:** React (or Next.js) with Tailwind CSS for rapid styling[cite: 58].

## 2. Design Tokens (Tailwind CSS Mapping)

### 2.1 Color Palette

- **Background (Base):** `#0D1117` (Deep IDE Gray)
- **Background (Surface/Panels):** `#161B22` (Elevated gray for chat inputs and tables)
- **Border/Divider:** `#30363D` (Muted structural lines to separate chat messages)
- **Primary Text:** `#C9D1D9` (Soft gray for high readability)
- **Secondary Text:** `#8B949E` (For timestamps and metadata)
- **Accent (Action/Success):** `#238636` (Terminal Green - for "Send" buttons and confirmed bookings)
- **Accent (Highlight/Link):** `#58A6FF` (Syntax Blue - for document links)
- **Accent (Pending):** `#D29922` (Yellow - for pending booking approvals)
- **Accent (Danger/Reject):** `#F85149` (Red - for rejected requests)

### 2.2 Typography

- **Prose/Chat:** `Inter`, `Roboto`, or `sans-serif`. Used for general conversation UI.
- **Data/Code:** `Fira Code`, `JetBrains Mono`, or `monospace`. Used strictly for document names, citation excerpts, timestamps, and tabular data.

---

## 3. Core Component Specifications

### 3.1 Web Chat UI

- [cite_start]**Layout:** Responsive web chat (desktop/mobile)[cite: 14]. Full-width edge-to-edge layout.
- [cite_start]**History:** Must display conversation history for the session[cite: 14].
- **Message Styles:** Use flat rows separated by bottom borders (`#30363D`). Do not use rounded chat bubbles.
  - User messages prefixed with `USER >` in monospace.
  - AI messages prefixed with `SYS >` in monospace.
- **Input Bar:** Sticky bottom area. Flat rectangular input field with a solid green (`#238636`) submit button.

### 3.2 Document-Aware Citations (RAG)

- [cite_start]**Requirement:** Answers must be grounded and include citations (doc name + link + excerpt)[cite: 10, 15].
- **Visuals:** Render citations directly below the text response as a monospace, terminal-style blockquote or code block.
- **Formatting Rules:**
  - Doc Name: Monospace text.
  - Link: Syntax Blue (`#58A6FF`) and clickable.
  - Excerpt: Encased in a muted gray blockquote.

### 3.3 Smart Resource Booking Flow

- [cite_start]**Requirement:** Check availability, suggest alternatives, and draft a booking request[cite: 17].
- **Display:** Do not use traditional calendar widgets. [cite_start]Show an availability check and alternate slot suggestions [cite: 54] in a dense, monospace grid or table layout.
- [cite_start]**Interaction:** Clicking a slot opens a minimalist inline form to confirm the booking request[cite: 86].

### 3.4 Admin/Status Dashboard

- [cite_start]**Requirement:** Quick admin/status page showing pending/approved/rejected requests[cite: 88].
- **Display:** A high-density data table.
- **Columns:** Monospace Request ID, User, Resource, Time, Status.
- **Status Indicators:** Use stark, colored pills (Terminal Green for Approved, Red for Rejected, Yellow for Pending).

## 4. Copilot Prompting Guide

- **Instruction:** When generating components, strictly adhere to Tailwind utility classes.
- **Instruction:** Avoid custom CSS files.
- **Instruction:** Prioritize flexbox for chat layouts and CSS grid for the booking availability display.
