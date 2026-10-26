import { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [themeMode, setThemeMode] = useState(() => {
    return localStorage.getItem('themeMode') || 'system';
  });

  const [colorTheme, setColorTheme] = useState(() => {
    return localStorage.getItem('colorTheme') || 'teal';
  });

  useEffect(() => {
    const root = document.documentElement;

    // Apply color theme
    if (colorTheme === 'teal') {
      root.removeAttribute('data-theme'); // default
    } else {
      root.setAttribute('data-theme', colorTheme);
    }
    
    localStorage.setItem('colorTheme', colorTheme);
  }, [colorTheme]);

  useEffect(() => {
    const root = document.documentElement;

    // Apply dark mode
    const applyMode = (mode) => {
      if (mode === 'dark') {
        root.classList.add('dark');
      } else if (mode === 'light') {
        root.classList.remove('dark');
      } else {
        // System
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      }
    };

    applyMode(themeMode);
    localStorage.setItem('themeMode', themeMode);

    // Listen for system changes if mode is 'system'
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (themeMode === 'system') {
        applyMode('system');
      }
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [themeMode]);

  return (
    <ThemeContext.Provider value={{ themeMode, setThemeMode, colorTheme, setColorTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
