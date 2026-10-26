import React from 'react';
import { ThemeSelector } from '../components/ThemeSelector';

export default function ThemeCustomizer() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Customize Your Experience</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">Personalize the appearance of QueueLess AI.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Side: Controls */}
        <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm transition-colors">
          <ThemeSelector showPreview={false} />
          
          <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700 flex gap-4">
            <button className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-sm transition-all transform active:scale-95">
              Apply Theme
            </button>
            <button className="px-6 py-2.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
              Reset to Default
            </button>
          </div>
        </div>

        {/* Right Side: Live Preview */}
        <div className="bg-slate-100 dark:bg-slate-900/50 p-8 rounded-2xl border border-slate-200 dark:border-slate-700 flex items-center justify-center transition-colors">
          <div className="w-full max-w-sm bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden transform scale-95 origin-center">
            {/* Fake Dashboard Header */}
            <div className="h-14 border-b border-slate-100 dark:border-slate-700 flex items-center px-4 justify-between">
              <div className="font-bold text-primary-600 dark:text-primary-400">QueueLess AI</div>
              <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700"></div>
            </div>
            
            {/* Fake Content */}
            <div className="p-5 space-y-5">
              <div className="flex justify-between items-center">
                <div className="text-sm font-semibold text-slate-900 dark:text-white">Active Token</div>
                <span className="px-2 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300 rounded-md text-[10px] font-bold uppercase">
                  Serving
                </span>
              </div>
              
              <div className="bg-primary-600 p-6 rounded-xl text-white text-center shadow-md">
                <div className="text-primary-100 text-xs font-medium mb-1">Your Number</div>
                <div className="text-4xl font-bold tracking-wider">H-024</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg border border-slate-100 dark:border-slate-600 text-center">
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">People Ahead</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">3</div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg border border-slate-100 dark:border-slate-600 text-center">
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">Estimated Wait</div>
                  <div className="text-xl font-bold text-primary-600 dark:text-primary-400 mt-1">12 min</div>
                </div>
              </div>

              <button className="w-full py-2.5 border-2 border-primary-600 text-primary-600 dark:text-primary-400 dark:border-primary-500 font-semibold rounded-lg text-sm hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors">
                View Queue
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
