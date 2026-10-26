import React, { useState } from 'react';

export default function Settings() {
  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    return localStorage.getItem('appLanguage') || 'en';
  });
  const [savedNotice, setSavedNotice] = useState(false);

  const languages = [
    { code: 'en', name: 'English', native: 'English', flag: '🇬🇧' },
    { code: 'ta', name: 'Tamil', native: 'தமிழ்', flag: '🇮🇳' },
  ];

  const handleSelectLanguage = (code) => {
    setSelectedLanguage(code);
    localStorage.setItem('appLanguage', code);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div className="max-w-4xl mx-auto pb-12">
      {/* Title */}
      <div className="mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
          Preferences
        </span>
        <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-main)] mt-1">
          Settings
        </h1>
        <p className="text-[var(--color-secondary)] mt-1 text-sm">
          Manage your regional and interface language preferences.
        </p>
      </div>

      {/* Main Settings Module Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Settings Sidebar */}
        <aside className="md:col-span-1 space-y-1">
          <button
            type="button"
            className="w-full text-left px-4 py-3 rounded-xl font-semibold text-sm bg-[var(--color-primary)] text-white shadow-xs flex items-center justify-between"
          >
            <span>🌐 Language</span>
            <span className="text-xs">✓</span>
          </button>
        </aside>

        {/* Content Panel */}
        <main className="md:col-span-3">
          <div className="bg-[var(--color-surface)] p-6 sm:p-8 rounded-[22px] border border-[var(--color-border-subtle)] shadow-xs">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--color-border-subtle)]">
              <div>
                <h2 className="text-xl font-bold text-[var(--color-text-main)]">
                  Language Preference
                </h2>
                <p className="text-xs text-[var(--color-secondary)] mt-1">
                  Choose your display language for the application.
                </p>
              </div>
              {savedNotice && (
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300 animate-fade-in">
                  Saved ✓
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {languages.map((lang) => {
                const isSelected = selectedLanguage === lang.code;
                return (
                  <button
                    type="button"
                    key={lang.code}
                    onClick={() => handleSelectLanguage(lang.code)}
                    className={`p-5 rounded-[18px] border text-left transition-all flex items-center justify-between cursor-pointer ${
                      isSelected
                        ? 'border-[var(--color-primary)] bg-[var(--color-accent-subtle)] shadow-xs'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-surface)] hover:border-[var(--color-primary)]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{lang.flag}</span>
                      <div>
                        <p className="font-bold text-sm text-[var(--color-text-main)]">
                          {lang.name}
                        </p>
                        <p className="text-xs text-[var(--color-secondary)] font-medium">
                          {lang.native}
                        </p>
                      </div>
                    </div>

                    <div
                      className={`w-5 h-5 rounded-full border flex items-center justify-center text-xs transition-colors ${
                        isSelected
                          ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                          : 'border-[var(--color-border-subtle)] text-transparent'
                      }`}
                    >
                      ✓
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-8 pt-6 border-t border-[var(--color-border-subtle)] text-xs text-[var(--color-secondary)] leading-relaxed">
              💡 Current selection is preserved across sessions via local preferences.
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
