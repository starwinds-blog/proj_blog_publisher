import React, { useState } from 'react';
import {
  CheckCircle2,
  FileEdit,
  GitCompare,
  LayoutDashboard,
  Moon,
  Rocket,
  Sparkles,
  Sun,
} from 'lucide-react';
import { OverviewPage } from './pages/OverviewPage';
import { StoryStudioPage } from './pages/StoryStudioPage';
import { ReviewGatePage } from './pages/ReviewGatePage';
import { PublishCenterPage } from './pages/PublishCenterPage';

export type NavTab = 'overview' | 'studio' | 'review' | 'publish';

export const App: React.FC = () => {
  const [tab, setTab] = useState<NavTab>('overview');
  const [selectedSlug, setSelectedSlug] = useState<string | undefined>('first-test-story');
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    document.documentElement.classList.contains('light') ? 'light' : 'dark'
  );

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.classList.toggle('light', next === 'light');
    try {
      localStorage.setItem('theme', next);
    } catch {
      /* ignore */
    }
  };

  const handleNavigate = (targetTab: NavTab, slug?: string) => {
    if (slug) {
      setSelectedSlug(slug);
    }
    setTab(targetTab);
  };

  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: '대시보드 홈 (파이프라인)', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'studio', label: '스토리 입력 & 초안 스튜디오', icon: <FileEdit className="w-4 h-4" /> },
    { id: 'review', label: 'Diff 검토 & 승인 게이트', icon: <GitCompare className="w-4 h-4" /> },
    { id: 'publish', label: '발행 센터 & 배포 설정', icon: <Rocket className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur border-b border-slate-800">
        <div className="max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div
            onClick={() => setTab('overview')}
            className="flex items-center gap-3 cursor-pointer"
          >
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-slate-100">
                AI Story-to-Blog Publisher
              </span>
              <span className="hidden md:inline-block ml-2 text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                Raw → Draft → Approve → Hugo Pages
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-1 overflow-x-auto">
            {navItems.map((item) => {
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setTab(item.id)}
                  className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition whitespace-nowrap cursor-pointer ${
                    active
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            {selectedSlug && (
              <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs text-slate-300 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                {selectedSlug}
              </span>
            )}
            <button
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label="Toggle theme"
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium border border-slate-700 text-slate-300 hover:bg-slate-800/70 transition cursor-pointer"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              <span className="hidden sm:inline">{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[96rem] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {tab === 'overview' && <OverviewPage onNavigate={handleNavigate} />}
        {tab === 'studio' && (
          <StoryStudioPage
            selectedSlug={selectedSlug}
            onSelectSlug={setSelectedSlug}
            onNavigate={handleNavigate}
          />
        )}
        {tab === 'review' && (
          <ReviewGatePage
            selectedSlug={selectedSlug}
            onSelectSlug={setSelectedSlug}
            onNavigate={handleNavigate}
          />
        )}
        {tab === 'publish' && (
          <PublishCenterPage
            selectedSlug={selectedSlug}
            onSelectSlug={setSelectedSlug}
          />
        )}
      </main>
    </div>
  );
};

export default App;
