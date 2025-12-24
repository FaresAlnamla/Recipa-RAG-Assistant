"use client";

import React, { useState, useRef, useEffect, FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  Loader2, AlertCircle, Copy, Check, Search, ArrowRight, 
  StopCircle, Trash2, Brain, BookOpen, MessageSquare, ChevronDown, ChevronUp 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { API_BASE_URL, SUGGESTED_QUESTIONS } from "@/lib/constants";

type HistoryEntry = { question: string; answer: string; };

// Types for Transparency Panels
type AgentStep = 'idle' | 'planning' | 'retrieving' | 'generating' | 'completed';

export default function QAEngine() {
  const { toast } = useToast();
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  
  // Split State for Transparency
  const [currentStep, setCurrentStep] = useState<AgentStep>('idle');
  const [agentThought, setAgentThought] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [isThoughtExpanded, setIsThoughtExpanded] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isCopied, setIsCopied] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // --- PERSISTENCE ---
  useEffect(() => {
    const saved = localStorage.getItem("recipa-history");
    if (saved) {
      try { setHistory(JSON.parse(saved)); } catch (e) { console.error("Failed to load history", e); }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("recipa-history", JSON.stringify(history));
  }, [history]);

  const clearHistory = () => {
    setHistory([]);
    setCurrentAnswer("");
    setAgentThought("");
    setSources([]);
    setCurrentStep('idle');
    localStorage.removeItem("recipa-history");
    toast({ title: "History Cleared" });
  };

  const handleCopy = async () => {
    if (!currentAnswer) return;
    try {
      await navigator.clipboard.writeText(currentAnswer);
      setIsCopied(true);
      toast({ title: "Copied to clipboard" });
      setTimeout(() => setIsCopied(false), 2000);
    } catch { toast({ title: "Failed to copy", variant: "destructive" }); }
  };

  const handleSubmit = async (e?: FormEvent, manualQuestion?: string) => {
    if (e) e.preventDefault();
    const queryText = manualQuestion || question;
    if (!queryText.trim()) { setError("Please enter a question"); return; }

    if (abortControllerRef.current) abortControllerRef.current.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setError("");
    setCurrentAnswer("");
    setAgentThought("");
    setSources([]);
    setCurrentStep('planning');
    setIsCopied(false);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: queryText.trim(), k: 3, history: history.slice(-3) }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      if (!response.body) throw new Error("Streaming not supported.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;

        // --- TRANSPARENCY PARSING LOGIC ---
        // Assuming backend markers: [THOUGHT]...[/THOUGHT], [SOURCES]...[/SOURCES], [ANSWER]...
        if (fullText.includes("[THOUGHT]")) {
            setCurrentStep('planning');
            const match = fullText.match(/\[THOUGHT\]([\s\S]*?)(?=\[SOURCES\]|\[ANSWER\]|$)/);
            if (match) setAgentThought(match[1].trim());
        }
        
        if (fullText.includes("[SOURCES]")) {
            setCurrentStep('retrieving');
            const match = fullText.match(/\[SOURCES\]([\s\S]*?)(?=\[ANSWER\]|$)/);
            if (match) {
                const sourceList = match[1].split("\n").filter(s => s.trim().length > 0);
                setSources(sourceList);
            }
        }

        if (fullText.includes("[ANSWER]")) {
            setCurrentStep('generating');
            const parts = fullText.split("[ANSWER]");
            setCurrentAnswer(parts[parts.length - 1].trim());
        } else if (!fullText.includes("[THOUGHT]") && !fullText.includes("[SOURCES]")) {
            // Fallback if no markers are present
            setCurrentAnswer(fullText);
        }
      }
      
      setCurrentStep('completed');
      setQuestion("");
      setHistory((prev) => [...prev, { question: queryText.trim(), answer: currentAnswer }].slice(-10));
    } catch (err: any) {
      if (err.name !== 'AbortError') setError(err.message || "Something went wrong.");
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <section id="qa-section" className="min-h-screen flex flex-col justify-center py-20 bg-white border-b border-gray-200 relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: "radial-gradient(#000 1px, transparent 1px)", backgroundSize: "32px 32px" }} />

      <div className="max-w-7xl mx-auto px-4 w-full relative z-10">
        <div className="text-center mb-16 md:mb-24">
          <h2 className="text-4xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-4">
            Ask Recipa<span className="text-orange-600">AI</span>
          </h2>
          <p className="text-lg md:text-2xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-medium">
              Transparent, citation-backed recipe intelligence.
          </p>
        </div>

        <div className="max-w-5xl mx-auto space-y-8">
          {/* INPUT PANEL */}
          <Card className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-200">
            <div className="h-2 bg-gradient-to-r from-orange-400 to-orange-600 w-full" />
            <CardContent className="p-6 md:p-10">
              <form onSubmit={handleSubmit} className="space-y-6">
                <Textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask about ingredients, low-cost cooking, or recipe substitutions..."
                  className="min-h-[120px] text-lg p-6 rounded-xl bg-gray-50 border-2 border-gray-200 focus-visible:border-orange-500 focus-visible:ring-0 transition-all"
                  disabled={isLoading}
                />
                
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED_QUESTIONS.map((s, idx) => (
                    <button key={idx} type="button" onClick={() => { setQuestion(s); handleSubmit(undefined, s); }}
                      className="text-xs font-bold bg-white text-gray-500 px-3 py-1.5 rounded-full border border-gray-200 hover:border-orange-400 hover:text-orange-600 transition-all">
                      {s}
                    </button>
                  ))}
                </div>

                <div className="flex gap-4">
                  <Button type="submit" disabled={isLoading || !question.trim()} className="flex-1 h-16 text-lg font-bold rounded-xl bg-gray-900 hover:bg-black text-white">
                    {isLoading ? <Loader2 className="animate-spin mr-2" /> : "Analyze Query"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* AGENT TRANSPARENCY PIPELINE */}
          {(isLoading || currentAnswer) && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
              
              {/* STEP 1: PLANNING/THOUGHT PANEL */}
              {(agentThought || currentStep === 'planning') && (
                <Card className="border-l-4 border-l-blue-500 shadow-sm overflow-hidden">
                  <button 
                    onClick={() => setIsThoughtExpanded(!isThoughtExpanded)}
                    className="w-full flex items-center justify-between p-4 bg-blue-50/30 hover:bg-blue-50 transition-colors"
                  >
                    <div className="flex items-center gap-3 text-blue-700 font-bold">
                      <Brain className={`h-5 w-5 ${currentStep === 'planning' ? 'animate-pulse' : ''}`} />
                      <span>Agent Reasoning</span>
                    </div>
                    {isThoughtExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {isThoughtExpanded && (
                    <CardContent className="p-6 text-slate-600 italic text-sm leading-relaxed border-t border-gray-100 bg-white">
                      {agentThought || <Skeleton className="h-4 w-full" />}
                    </CardContent>
                  )}
                </Card>
              )}

              {/* STEP 2: SOURCES PANEL */}
              {(sources.length > 0 || currentStep === 'retrieving') && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {currentStep === 'retrieving' && sources.length === 0 ? (
                    [1,2,3].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)
                  ) : (
                    sources.map((source, i) => (
                      <div key={i} className="p-4 rounded-xl border border-orange-100 bg-orange-50/30 flex items-start gap-3 group hover:border-orange-300 transition-all">
                        <BookOpen className="h-5 w-5 text-orange-600 mt-1 shrink-0" />
                        <div className="text-xs text-orange-900 font-medium line-clamp-3">
                          {source}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* STEP 3: ANSWER PANEL */}
              {(currentAnswer || currentStep === 'generating') && (
                <Card className="shadow-2xl border-2 border-gray-100 rounded-2xl overflow-hidden">
                  <CardHeader className="border-b border-gray-50 flex flex-row justify-between items-center bg-white py-6 px-8">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-orange-600 rounded-lg text-white">
                            <MessageSquare className="h-5 w-5" />
                        </div>
                        <CardTitle className="text-xl font-bold">Expert Synthesis</CardTitle>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleCopy} className="rounded-full">
                            {isCopied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                            {isCopied ? "Saved" : "Copy"}
                        </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-8 md:p-12 bg-white">
                    {currentStep === 'generating' && !currentAnswer ? (
                        <div className="space-y-4">
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-[90%]" />
                            <Skeleton className="h-4 w-[95%]" />
                        </div>
                    ) : (
                        <div className="prose prose-lg prose-slate max-w-none prose-strong:text-orange-700 prose-headings:text-slate-900">
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                                // Custom Citation Component logic can be added here
                                strong: ({node, ...props}) => <strong className="text-orange-600 font-extrabold" {...props} />,
                                table: ({node, ...props}) => <div className="overflow-x-auto my-6"><table className="w-full border-collapse" {...props} /></div>,
                                th: ({node, ...props}) => <th className="bg-slate-50 p-4 border border-slate-200 text-left" {...props} />,
                                td: ({node, ...props}) => <td className="p-4 border border-slate-100" {...props} />
                            }}
                        >
                            {currentAnswer}
                        </ReactMarkdown>
                        </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}