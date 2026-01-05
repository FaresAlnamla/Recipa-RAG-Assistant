import React from "react";
import { ARCHITECTURE_STEPS } from "@/lib/constants";

export default function Architecture() {
  return (
    <section
      id="how-it-works"
      className="min-h-screen flex flex-col justify-center py-20 bg-white border-b border-gray-200 relative overflow-hidden"
    >
      {/* Background Pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(#000 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="max-w-7xl mx-auto px-4 w-full relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-4">
            How It Works
          </h2>
          <div className="w-24 h-2 bg-orange-500 mx-auto mb-6 rounded-full" />
          <p className="text-lg md:text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-medium">
            Multi-agent system that routes, retrieves, evaluates, and remembers.
          </p>
        </div>

        {/* Grid Layout: 1 col on mobile, 2 on tablet, 3 on desktop */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {ARCHITECTURE_STEPS.map((item, idx) => (
            <div
              key={idx}
              className="group h-full p-8 rounded-2xl border-2 border-orange-300 bg-gradient-to-br from-orange-50 to-white hover:from-orange-100 hover:to-white hover:shadow-xl transition-all duration-300 shadow-lg"
            >
              <div className="flex flex-col items-start gap-6 h-full">
                <div className="w-14 h-14 bg-orange-600 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                  <item.icon className="h-7 w-7 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold text-gray-900 mb-3">
                    {item.title}
                  </h3>
                  <p className="text-slate-600 leading-relaxed text-sm md:text-base">
                    {item.text}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
