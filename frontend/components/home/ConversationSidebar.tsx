/**
 * ConversationSidebar Component
 * Shows conversation history for the current session
 */

"use client";

import React from "react";
import { X, MessageSquare, Copy, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface ConversationSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  history: Message[];
  onSelectMessage: (message: string) => void;
  onClearHistory: () => void;
}

export default function ConversationSidebar({
  isOpen,
  onClose,
  history,
  onSelectMessage,
  onClearHistory,
}: ConversationSidebarProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <Card className="fixed left-0 top-0 h-screen w-80 bg-white shadow-2xl z-50 rounded-none flex flex-col border-r border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-orange-600" />
            <h2 className="text-xl font-bold">Conversation</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="lg:hidden"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {history.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-8">
              No conversation yet. Start asking questions!
            </p>
          ) : (
            history
              .filter((msg) => msg.role === "user" || msg.role === "assistant")
              .map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    msg.role === "user"
                      ? "bg-orange-100 border border-orange-300 hover:bg-orange-200"
                      : "bg-gray-100 border border-gray-300 hover:bg-gray-200"
                  }`}
                  onClick={() => onSelectMessage(msg.content)}
                >
                  <p className="text-xs font-bold text-gray-600 mb-1">
                    {msg.role === "user" ? "You" : "RecipaAI"}
                  </p>
                  <p className="text-sm text-gray-800 line-clamp-3">
                    {msg.content}
                  </p>
                </div>
              ))
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="border-t border-gray-200 p-4">
            <Button
              variant="destructive"
              className="w-full"
              onClick={onClearHistory}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear History
            </Button>
          </div>
        )}
      </Card>
    </>
  );
}
