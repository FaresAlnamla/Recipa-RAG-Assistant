/**
 * API Client Service for Recipa Backend
 * Handles all communication with FastAPI backend
 */

export interface SourceItem {
  page?: number;
  page_label?: string;
  source?: string;
  book_name?: string;  // ✅ NEW: Friendly book name for display
  snippet: string;
}

export interface EvaluationItem {
  supported: boolean;
  confidence: number;
  reasons: string[];
  facts_checked: string[];
}

export interface AgentAskResponse {
  answer: string;
  sources: SourceItem[];
  evaluation: EvaluationItem;
  filtered_out: any[];
}

export interface HistoryItem {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface HistoryResponse {
  session_id: string;
  history: HistoryItem[];
}

export interface StreamEvent {
  type: "meta" | "token" | "done" | "error";
  session_id?: string;
  token?: string;
  answer?: string;
  sources?: SourceItem[];
  evaluation?: EvaluationItem;
  filtered_out?: any[];
  error?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  /**
   * Ask a question to the agent (non-streaming)
   * Synchronous response with answer, sources, evaluation, and filtered chunks
   */
  async askAgent(
    question: string,
    sessionId: string = "default"
  ): Promise<AgentAskResponse> {
    try {
      const response = await fetch(`${this.baseURL}/agent/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data: AgentAskResponse = await response.json();
      return data;
    } catch (error) {
      throw new Error(
        `Failed to ask agent: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  }

  /**
   * Stream answer from agent (streaming response)
   * Yields events as they arrive from the server
   */
  async *askAgentStream(
    question: string,
    sessionId: string = "default"
  ): AsyncGenerator<StreamEvent, void, unknown> {
    try {
      const response = await fetch(`${this.baseURL}/agent/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Streaming not supported");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        buffer += text;

        // Parse Server-Sent Events
        const lines = buffer.split("\n");
        buffer = lines[lines.length - 1]; // Keep incomplete line in buffer

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i];
          if (line.startsWith("data: ")) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));
              yield event;
            } catch (e) {
              console.error("Failed to parse SSE event:", e);
            }
          }
        }
      }

      // Process final buffer if any
      if (buffer && buffer.startsWith("data: ")) {
        try {
          const event: StreamEvent = JSON.parse(buffer.slice(6));
          yield event;
        } catch (e) {
          console.error("Failed to parse final SSE event:", e);
        }
      }
    } catch (error) {
      yield {
        type: "error",
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  /**
   * Get conversation history for a session
   */
  async getHistory(sessionId: string = "default"): Promise<HistoryResponse> {
    try {
      const response = await fetch(
        `${this.baseURL}/agent/memory/history?session_id=${encodeURIComponent(
          sessionId
        )}`,
        { method: "GET" }
      );

      if (!response.ok) {
        // If no history found, return empty
        if (response.status === 404) {
          return { session_id: sessionId, history: [] };
        }
        throw new Error(`API Error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(
        `Failed to get history: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  }

  /**
   * Clear all messages for a session
   */
  async clearSession(sessionId: string = "default"): Promise<void> {
    try {
      const response = await fetch(`${this.baseURL}/agent/memory/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
    } catch (error) {
      throw new Error(
        `Failed to clear session: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  }

  /**
   * Check backend health
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiClient = new APIClient(API_BASE_URL);
