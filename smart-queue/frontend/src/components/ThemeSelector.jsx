import { useTheme } from '../context/ThemeContext';
import { SunIcon, MoonIcon, ComputerDesktopIcon, CheckIcon } from '@heroicons/react/24/outline';

const colorThemes = [
  { id: 'teal', name: 'Teal', colorClass: 'bg-[#0F766E]' },
  { id: 'blue', name: 'Blue', colorClass: 'bg-[#2563EB]' },
  { id: 'purple', name: 'Purple', colorClass: 'bg-[#7C3AED]' },
  { id: 'green', name: 'Green', colorClass: 'bg-[#16A34A]' },
  { id: 'orange', name: 'Orange', colorClass: 'bg-[#EA580C]' },
  { id: 'red', name: 'Red', colorClass: 'bg-[#DC2626]' },
];

export const ThemeSelector = ({ showPreview = true }) => {
  const { themeMode, setThemeMode, colorTheme, setColorTheme } = useTheme();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-3">
          Theme Mode
        </h3>
        <div className="flex gap-3">
          <button
            onClick={() => setThemeMode('light')}
            className={`flex flex-col items-center justify-center p-3 w-24 rounded-xl border ${
              themeMode === 'light'
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
            } transition-colors`}
          >
            <SunIcon className="w-6 h-6 mb-2" />
            <span className="text-xs font-medium">Light</span>
          </button>
          
          <button
            onClick={() => setThemeMode('dark')}
            className={`flex flex-col items-center justify-center p-3 w-24 rounded-xl border ${
              themeMode === 'dark'
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
            } transition-colors`}
          >
            <MoonIcon className="w-6 h-6 mb-2" />
            <span className="text-xs font-medium">Dark</span>
          </button>

          <button
            onClick={() => setThemeMode('system')}
            className={`flex flex-col items-center justify-center p-3 w-24 rounded-xl border ${
              themeMode === 'system'
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
            } transition-colors`}
          >
            <ComputerDesktopIcon className="w-6 h-6 mb-2" />
            <span className="text-xs font-medium">System</span>
          </button>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-3">
          Accent Color
        </h3>
        <div className="flex flex-wrap gap-4">
          {colorThemes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => setColorTheme(theme.id)}
              className={`relative flex items-center justify-center w-10 h-10 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:focus:ring-offset-slate-900 transition-transform hover:scale-110 ${
                colorTheme === theme.id ? 'ring-2 ring-offset-2 ring-primary-500 dark:ring-offset-slate-900' : ''
              } ${theme.colorClass}`}
              title={theme.name}
            >
              {colorTheme === theme.id && (
                <CheckIcon className="w-5 h-5 text-white" strokeWidth={3} />
              )}
            </button>
          ))}
        </div>
      </div>

      {showPreview && (
        <div className="mt-8">
          <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-3">
            Live Preview
          </h3>
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 space-y-4">
            <div className="flex gap-4">
              <button className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg shadow-sm transition-colors">
                Primary Button
              </button>
              <button className="px-4 py-2 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-medium rounded-lg transition-colors">
                Secondary Button
              </button>
            </div>
            <div className="flex gap-2">
              <span className="px-3 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300 rounded-full text-xs font-bold uppercase">
                Active Badge
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
