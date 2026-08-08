'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Shield, Sparkles, HelpCircle, PhoneCall, AlertTriangle, RefreshCw, Radio } from 'lucide-react';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  micError?: boolean;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  micError = false,
  ref,
  ...props
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  if (micError) {
    return (
      <div 
        ref={ref} 
        className="w-full max-w-md mx-auto px-4 text-center animate-in fade-in zoom-in-95 duration-300"
        {...props}
      >
        <div className="relative mb-6 mx-auto flex items-center justify-center size-20 rounded-full bg-destructive/10 border border-destructive/30 text-destructive shadow-inner">
          <AlertTriangle className="size-10" />
        </div>

        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Microphone Access Blocked</h2>
        <p className="text-slate-600 mt-3 text-sm leading-relaxed">
          The assistant cannot hear you because microphone access is blocked. Please enable it in your browser settings to continue.
        </p>

        <div className="w-full bg-destructive/5 border border-destructive/20 rounded-2xl p-5 mt-6 text-left space-y-4 shadow-sm">
          <h4 className="text-xs font-semibold text-destructive uppercase tracking-wider">How to Enable:</h4>
          <ol className="text-xs text-slate-600 space-y-3 list-decimal list-inside leading-relaxed">
            <li>Look at the address bar at the top of your browser window.</li>
            <li>Click the <strong>lock</strong> or <strong>microphone icon</strong> next to the URL.</li>
            <li>Change the <strong>Microphone</strong> setting to <strong>Allow</strong>.</li>
            <li>Click the button below to reload the page.</li>
          </ol>
        </div>

        <Button
          onClick={() => window.location.reload()}
          size="lg"
          variant="destructive"
          className="mt-8 w-64 rounded-full font-semibold flex items-center justify-center gap-2 cursor-pointer shadow-lg"
        >
          <RefreshCw className="size-4" />
          <span>Reload Page</span>
        </Button>
      </div>
    );
  }

  return (
    <div 
      ref={ref} 
      className="w-full max-w-6xl mx-auto px-2 md:px-4 py-4 flex flex-col items-center justify-center animate-in fade-in duration-500"
      {...props}
    >
      {/* 2-Card Layout Format */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full items-stretch min-h-[500px]">
        {/* Left Card: Assistant Avatar & Start Call */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 md:p-8 flex flex-col justify-between items-center text-center relative overflow-hidden">
          
          {/* Top Status */}
          <div className="w-full flex items-center justify-center mb-4">
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-sky-700 bg-sky-50 px-3 py-1 rounded-full border border-sky-100">
              <Sparkles className="size-3.5 text-amber-500" />
              Citizen AI Voice Assistant
            </span>
          </div>

          {/* Central Avatar with Glow Ring */}
          <div className="relative my-4 flex items-center justify-center">
            {/* Pulsing Concentric Outer Ring */}
            <div className="absolute size-48 md:size-52 rounded-full border-2 border-amber-400/50 animate-ping duration-1000 opacity-40 pointer-events-none" />
            <div className="absolute size-44 md:size-48 rounded-full border-4 border-amber-400 shadow-xl shadow-amber-500/20 pointer-events-none" />
            
            {/* Avatar Image Circle */}
            <div className="relative size-36 md:size-40 rounded-full overflow-hidden border-4 border-white shadow-lg bg-sky-50">
              <img 
                src="/jan-sahay-avatar.png" 
                alt="Citizen AI Voice Assistant" 
                className="size-full object-cover" 
                onError={(e) => {
                  // Fallback if image fails to load
                  (e.target as HTMLImageElement).src = '/sam-avatar.png';
                }}
              />
            </div>
          </div>

          {/* Title & Description */}
          <div className="space-y-2 max-w-md">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Ready to Connect...
            </h2>
            <p className="text-slate-500 text-xs md:text-sm leading-relaxed">
              Ask about PM-Kisan, report cyber crimes, verify UPI links, or ask for basic savings guidance.
            </p>
          </div>

          {/* Start Call Button */}
          <Button
            size="lg"
            onClick={onStartCall}
            className="mt-6 w-full max-w-xs rounded-full font-mono text-xs font-bold tracking-wider uppercase bg-amber-500 hover:bg-amber-600 text-slate-950 transition-all duration-300 shadow-lg shadow-amber-500/20 cursor-pointer py-6 flex items-center justify-center gap-2"
          >
            <PhoneCall className="size-4" />
            <span>{startButtonText || "Start Audio Session"}</span>
          </Button>

          {/* TRY SAYING Section */}
          <div className="w-full mt-6 pt-4 border-t border-slate-100 text-left">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2 font-mono">
              TRY SAYING
            </span>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={onStartCall}
                className="inline-flex items-center gap-1.5 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors px-3 py-1.5 rounded-full border border-slate-200/80 cursor-pointer"
              >
                <HelpCircle className="size-3.5 text-slate-400" />
                <span>"How do I report UPI fraud?"</span>
              </button>
              <button 
                onClick={onStartCall}
                className="inline-flex items-center gap-1.5 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors px-3 py-1.5 rounded-full border border-slate-200/80 cursor-pointer"
              >
                <HelpCircle className="size-3.5 text-slate-400" />
                <span>"Tell me about PM-Kisan scheme"</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Card: Live Transcript Panel Preview */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between h-full min-h-[480px]">
          {/* Transcript Header */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <span className="text-xs font-bold text-slate-600 font-mono tracking-wider uppercase flex items-center gap-2">
              LIVE TRANSCRIPT
            </span>
            <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-600 border border-emerald-200 font-mono font-bold text-[10px] px-2.5 py-0.5 rounded-full">
              <Radio className="size-3 text-emerald-500 animate-pulse" />
              READY
            </span>
          </div>

          {/* Sample Transcript Bubbles preview */}
          <div className="flex-1 overflow-y-auto py-6 space-y-4 flex flex-col justify-center">
            {/* Agent Message Demo */}
            <div className="space-y-1">
              <span className="text-xs font-medium text-slate-400 ml-1">Citizen Assistant</span>
              <div className="bg-slate-100 text-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm max-w-[85%] font-normal shadow-2xs leading-relaxed">
                Namaste! Welcome to Citizen AI Voice Assistant. Click <strong>Start Audio Session</strong> to speak directly to me.
              </div>
            </div>

            {/* User Message Demo */}
            <div className="space-y-1 flex flex-col items-end">
              <span className="text-xs font-medium text-slate-400 mr-1">You</span>
              <div className="bg-sky-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%] font-normal shadow-2xs leading-relaxed">
                How do I report a suspicious UPI link?
              </div>
            </div>

            {/* Agent Response Demo */}
            <div className="space-y-1">
              <span className="text-xs font-medium text-slate-400 ml-1">Citizen Assistant</span>
              <div className="bg-slate-100 text-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm max-w-[85%] font-normal shadow-2xs leading-relaxed">
                You can immediately report cyber fraud on the national cyber crime portal 1930. I can guide you step by step.
              </div>
            </div>
          </div>

          {/* Card Footer notice */}
          <div className="pt-3 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-400 flex items-center justify-center gap-1.5">
              <Shield className="size-3.5 text-slate-400" />
              End-to-end encrypted audio stream
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
