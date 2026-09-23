/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

export type Language = 'es' | 'en';
interface LanguageContextValue { language: Language; setLanguage: (language: Language) => void; }
const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const stored = window.localStorage.getItem('review-desk-language');
    return stored === 'en' ? 'en' : 'es';
  });
  const value = useMemo(() => ({ language, setLanguage: (next: Language) => { setLanguageState(next); window.localStorage.setItem('review-desk-language', next); } }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) throw new Error('useLanguage must be used inside LanguageProvider');
  return value;
}

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();
  const next = language === 'es' ? 'en' : 'es';
  return <button type="button" className="language-button" onClick={() => setLanguage(next)} aria-label={language === 'es' ? 'Cambiar a inglés' : 'Switch to Spanish'}>{next === 'en' ? 'English' : 'Español'}</button>;
}
