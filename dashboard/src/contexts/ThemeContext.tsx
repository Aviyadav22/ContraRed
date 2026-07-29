import { useEffect, useState, type ReactNode } from 'react';
import { ThemeContext, type Theme } from './theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('contrared-theme') as Theme | null;
    return saved || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('contrared-theme', theme);
  }, [theme]);

  const toggleTheme = () => setThemeState(t => t === 'dark' ? 'light' : 'dark');
  const setTheme = (t: Theme) => setThemeState(t);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
