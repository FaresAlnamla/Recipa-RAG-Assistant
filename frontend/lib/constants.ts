// lib/constants.ts
import {
  BookOpen,
  Database,
  Sparkles,
  Navigation,
  CheckCircle,
  History,
} from "lucide-react";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const GITHUB_URL =
  "https://github.com/WalidAlsafadi/recipa-rag-assistant";

export const NAV_SECTIONS = [
  { name: "Home", id: "hero" },
  { name: "Architecture", id: "how-it-works" },
  { name: "Ask RecipaAI", id: "qa-section" },
  { name: "Team", id: "team" },
];

export const SUGGESTED_QUESTIONS = [
  "How do I make chocolate mug cake?",
  "What is mini egg muffins ingredients?",
  "How to make loaded sweet potato?",
];

export const ARCHITECTURE_STEPS = [
  {
    icon: Navigation,
    title: "Router",
    text: "Determines if the question is cookbook-related, a catalog request, or out-of-scope. Handles follow-ups intelligently.",
  },
  {
    icon: Database,
    title: "Retrieval",
    text: "Searches the cookbook using semantic vector search (Chroma). Returns relevant recipe chunks with metadata (source, page).",
  },
  {
    icon: Sparkles,
    title: "LLM",
    text: "Synthesizes an answer using ONLY the retrieved cookbook context. Supports streaming tokens for real-time UX.",
  },
  {
    icon: CheckCircle,
    title: "Evaluation",
    text: "Verifies the answer is supported by retrieved chunks. Produces confidence scores and facts-checked metadata.",
  },
  {
    icon: History,
    title: "Memory",
    text: "Persists chat messages and recipe context in SQLite. Enables follow-ups and maintains session history.",
  },
  {
    icon: BookOpen,
    title: "Response",
    text: "Returns the final answer with sources (full book name + page), evaluation metrics, and structured metadata.",
  },
];

export const TEAM_MEMBERS = [
  {
    name: "Walid Alsafadi",
    role: "RAG & Backend Lead",
    image: "/walid.webp",
    linkedin: "https://www.linkedin.com/in/walidalsafadi",
    github: "https://github.com/walidalsafadi",
    email: "mailto:walid.k.alsafadi@gmail.com",
  },
  {
    name: "Fares Alnamla",
    role: "AI Agent Engineer",
    image: "/fares.webp",
    linkedin: "https://www.linkedin.com/in/faresalnamla",
    github: "https://github.com/FaresAlnamla",
    email: "mailto:faresalnam@gmail.com",
  },
  {
    name: "Ahmed Alyazuri",
    role: "Frontend Developer",
    image: "/ahmed.webp",
    linkedin: "https://www.linkedin.com/in/ahmed-alyazuri",
    github: "https://github.com/AhmedAl-Yazuri",
    email: "mailto:ahmedalyazuri@gmail.com",
  },
];
