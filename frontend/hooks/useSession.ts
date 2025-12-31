/**
 * Hook to manage session state
 * Generates and persists a unique session ID
 */

import { useState, useEffect } from "react";

export const useSession = () => {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    // Try to load existing session from localStorage
    const stored = localStorage.getItem("recipa-session-id");

    if (stored) {
      setSessionId(stored);
    } else {
      // Generate new session ID (timestamp + random)
      const newSessionId = `session-${Date.now()}-${Math.random()
        .toString(36)
        .substr(2, 9)}`;
      localStorage.setItem("recipa-session-id", newSessionId);
      setSessionId(newSessionId);
    }
  }, []);

  const resetSession = () => {
    const newSessionId = `session-${Date.now()}-${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    localStorage.setItem("recipa-session-id", newSessionId);
    setSessionId(newSessionId);
  };

  return { sessionId, resetSession };
};
