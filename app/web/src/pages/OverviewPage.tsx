import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileText,
  FolderGit2,
  PlusCircle,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { NavTab } from '../App';
import { OverviewResponse, StorySummary } from '../types';

interface Props {
  onNavigate: (tab: NavTab, slug?: string) => void;
}

const STAGE_BADGES: Record<string, { label: string; cls: string }> = {
  raw: { label: '원본 (Raw)', cls: 'bg-slate-800 text-slate-300 border-slate-700' },
  draft: { label: '초안 검토대기 (Draft)', cls: 'bg-amber-950/70 text-amber-300 border-amber-800/70' },
  approved: { label: '승인 완료 (Approved)', cls: 'bg-indigo-950/70 text-indigo-300 border-indigo-800/70' },
  staged: { label: '로컬 스테이징 (Staged)', cls: 'bg-sky-950/70 text-sky-300 border-sky-800/70' },
  pending_verification: { label: '배포 확인대기 (Pending)', cls: 'bg-purple-950/70 text-purple-300 border-purple-800/70' },
  published: { label: '발행 완료 (Published)', cls: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/70' },
  deploy_failed: { label: '배포 실패 (Failed)', cls: 'bg-rose-950/70 text-rose-300 border-rose-800/70' },
};

export const OverviewPage: React.FC<Props> = ({ onNavigate }) => {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/overview');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Failed to load overview', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  if (loading && !data) {
    return (
      <div className="p-8 text-center text-slate-400">
        파이프라인 및 환경 상태를 불러오는 중입니다...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center text-rose-400">
        대시보드 데이터를 불러오지 못했습니다.
      </div>
    );
  }

  const { counts, env, stories, recent_logs } = data;

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-950 border border-indigo-800/70 text-indigo-300 text-xs font-medium mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            로컬 우선 · 원문 보존 · 명시적 승인 배포
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-100">
            AI Story-to-Blog Publisher 워크스페이스
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            자유 형식 메모나 이야기를 입력하면 원문 의미를 보존하며 Hugo 마크다운 초안과 Diff를 생성하고, 승인 후 GitHub Pages로 발행합니다.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={fetchOverview}
            className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl border border-slate-700 bg-slate-800/70 hover:bg-slate-800 text-xs sm:text-sm text-slate-200 cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            새로고침
          </button>
          <button
            onClick={() => onNavigate('studio')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/25 cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            새 스토리 작성하기
          </button>
        </div>
      </div>

      {/* Pipeline Stage KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: '전체 스토리', val: counts.total, sub: 'stories/*', color: 'text-slate-100' },
          { label: '원본 (Raw)', val: counts.raw, sub: 'stories/raw', color: 'text-slate-300' },
          { label: '초안 검토대기', val: counts.draft, sub: 'stories/drafts', color: 'text-amber-400' },
          { label: '승인 완료', val: counts.approved, sub: 'stories/approved', color: 'text-indigo-400' },
          { label: '사이트 스테이징', val: counts.staged, sub: 'site/content/posts', color: 'text-sky-400' },
          { label: '발행 완료', val: counts.published, sub: 'GitHub Pages Live', color: 'text-emerald-400' },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between"
          >
            <span className="text-xs text-slate-400">{kpi.label}</span>
            <div className={`text-2xl font-bold mt-2 ${kpi.color}`}>{kpi.val}</div>
            <span className="text-[11px] text-slate-500 font-mono mt-1">{kpi.sub}</span>
          </div>
        ))}
      </div>

      {/* Stories Pipeline List & Environment Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 cols: Story Pipeline Table */}
        <div className="lg:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              스토리 및 게시물 파이프라인 목록
            </h2>
            <span className="text-xs text-slate-400">클릭하여 편집 · Diff 검토 · 발행 이동</span>
          </div>

          <div className="space-y-3">
            {stories.map((st: StorySummary) => {
              const badge = STAGE_BADGES[st.stage] || STAGE_BADGES.draft;
              return (
                <div
                  key={st.slug}
                  className="rounded-xl bg-slate-950/70 border border-slate-800/90 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-700 transition"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full border ${badge.cls}`}>
                        {badge.label}
                      </span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {st.slug}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/50">
                        템플릿: {st.template}
                      </span>
                      {st.validation_valid === true && (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" /> 검증 통과
                        </span>
                      )}
                      {st.validation_valid === false && (
                        <span className="inline-flex items-center gap-1 text-xs text-rose-400">
                          <AlertTriangle className="w-3.5 h-3.5" /> 오류 {st.validation_errors_count}건
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm sm:text-base font-semibold text-slate-100">{st.title}</h3>
                    {st.description && (
                      <p className="text-xs text-slate-400 line-clamp-2">{st.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => onNavigate('studio', st.slug)}
                      className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer"
                    >
                      편집 스튜디오
                    </button>
                    <button
                      onClick={() => onNavigate('review', st.slug)}
                      className="px-3 py-1.5 rounded-lg border border-indigo-700/70 bg-indigo-950/60 hover:bg-indigo-900/60 text-xs text-indigo-200 cursor-pointer"
                    >
                      Diff & 승인
                    </button>
                    <button
                      onClick={() => onNavigate('publish', st.slug)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white cursor-pointer"
                    >
                      <Rocket className="w-3.5 h-3.5" />
                      발행
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 1 col: Environment & Guardrails */}
        <div className="space-y-6">
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              로컬 환경 & 도구 점검 (Phase 0)
            </h2>
            <div className="space-y-2 text-xs">
              {Object.entries(env.tools).map(([key, info]) => (
                <div
                  key={key}
                  className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80"
                >
                  <span className="font-mono font-medium text-slate-200">{key}</span>
                  {info.installed ? (
                    <span className="text-emerald-400 font-mono truncate max-w-[180px]">
                      ✓ {info.version || 'Installed'}
                    </span>
                  ) : (
                    <span className="text-amber-400 font-mono">
                      {info.required ? '✗ 필수 미설치' : '○ 선택(미설치)'}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {env.warnings.length > 0 && (
              <div className="rounded-xl bg-amber-950/40 border border-amber-800/60 p-3 space-y-1.5 text-xs text-amber-200">
                <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  환경 참고 사항
                </div>
                {env.warnings.map((w, idx) => (
                  <p key={idx} className="leading-relaxed">
                    • {w}
                  </p>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-indigo-400" />
              최근 파이프라인 실행 로그
            </h2>
            {recent_logs.length === 0 ? (
              <p className="text-xs text-slate-400">아직 기록된 대시보드 작업 로그가 없습니다.</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {recent_logs.map((log) => (
                  <div
                    key={log.id}
                    className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-indigo-300">{log.slug}</span>
                      <span className="text-[11px] text-slate-400">{log.action}</span>
                    </div>
                    <p className="text-slate-300">{log.summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
