/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLanguage } from './i18n';

export type Theme = 'light' | 'dark';
interface ThemeContextValue { theme: Theme; setTheme: (theme: Theme) => void; }
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => window.localStorage.getItem('review-desk-theme') === 'dark' ? 'dark' : 'light');
  useEffect(() => { document.documentElement.dataset.theme = theme; window.localStorage.setItem('review-desk-theme', theme); }, [theme]);
  const value = useMemo(() => ({ theme, setTheme: (next: Theme) => setThemeState(next) }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme must be used inside ThemeProvider');
  return value;
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { language } = useLanguage();
  const dark = theme === 'dark';
  const label = language === 'es' ? (dark ? 'Claro' : 'Oscuro') : (dark ? 'Light' : 'Dark');
  return <button type="button" className="theme-toggle" aria-pressed={dark} aria-label={language === 'es' ? `Cambiar a tema ${dark ? 'claro' : 'oscuro'}` : `Switch to ${dark ? 'light' : 'dark'} theme`} title={label} onClick={() => setTheme(dark ? 'light' : 'dark')}><span aria-hidden="true">{dark ? '☀' : '☾'}</span><span className="theme-toggle__label">{label}</span></button>;
}
