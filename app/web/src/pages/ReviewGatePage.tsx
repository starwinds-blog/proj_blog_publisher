import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  GitCompare,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ThumbsUp,
} from 'lucide-react';
import { NavTab } from '../App';
import { StoryDetail, StorySummary } from '../types';

interface Props {
  selectedSlug?: string;
  onSelectSlug: (slug: string) => void;
  onNavigate: (tab: NavTab, slug?: string) => void;
}

const CHECK_LABELS: Record<string, string> = {
  front_matter_valid: 'Hugo YAML Front Matter 필수 키/형식 검증',
  code_blocks_balanced: '코드 블록(```) 짝 일치 및 문법 안정성',
  links_and_images_valid: '로컬 이미지/링크 참조 무결성',
  no_secrets_found: '프라이버시 · API 키 · 토큰 미포함 검증',
  raw_code_preserved: '원문(Raw) 내 코드 블록 100% 보존 검증',
};

export const ReviewGatePage: React.FC<Props> = ({
  selectedSlug,
  onSelectSlug,
  onNavigate,
}) => {
  const [stories, setStories] = useState<StorySummary[]>([]);
  const [detail, setDetail] = useState<StoryDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const loadStories = async () => {
    const res = await fetch('/api/blog/stories');
    const json = await res.json();
    const list: StorySummary[] = json.items || [];
    setStories(list);
    if (!selectedSlug && list.length > 0) {
      onSelectSlug(list[0].slug);
    }
  };

  const loadDetail = async (slug: string) => {
    const res = await fetch(`/api/blog/stories/${encodeURIComponent(slug)}`);
    if (res.ok) {
      setDetail(await res.json());
    }
  };

  useEffect(() => {
    loadStories();
  }, []);

  useEffect(() => {
    if (selectedSlug) {
      loadDetail(selectedSlug);
    }
  }, [selectedSlug]);

  const handleRevalidate = async () => {
    if (!selectedSlug) return;
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch(`/api/blog/stories/${encodeURIComponent(selectedSlug)}/validate`, {
        method: 'POST',
      });
      const json = await res.json();
      await loadDetail(selectedSlug);
      setBanner({
        type: json.valid ? 'ok' : 'err',
        text: json.valid
          ? '품질 및 보안 가드레일 검증을 모두 통과했습니다.'
          : `검증 실패: 오류 ${json.errors?.length || 0}건이 발견되었습니다.`,
      });
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedSlug) return;
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch(`/api/blog/stories/${encodeURIComponent(selectedSlug)}/approve`, {
        method: 'POST',
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || '승인 처리에 실패했습니다.');
      }
      setDetail(json);
      await loadStories();
      setBanner({
        type: 'ok',
        text: `승인 완료! stories/approved/${selectedSlug}.md 생성 및 draft: false 전환이 완료되었습니다.`,
      });
    } catch (err: unknown) {
      setBanner({
        type: 'err',
        text: err instanceof Error ? err.message : '승인 오류',
      });
    } finally {
      setBusy(false);
    }
  };

  const val = detail?.validation;
  const diffLines = (detail?.review_report?.diff || '').split('\n');

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-400" />
            원문 대비 Diff 검토 &amp; 발행 승인 게이트
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            원문 의미 보존 여부와 보안/메타데이터 검증 결과를 확인한 뒤 명시적으로 승인(<code className="text-indigo-300">stories/approved/</code>)합니다.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <select
            value={selectedSlug || ''}
            onChange={(e) => {
              onSelectSlug(e.target.value);
              setBanner(null);
            }}
            className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs sm:text-sm text-slate-200"
          >
            {stories.map((s) => (
              <option key={s.slug} value={s.slug}>
                [{s.stage}] {s.title} ({s.slug})
              </option>
            ))}
          </select>

          <button
            onClick={handleRevalidate}
            disabled={busy || !selectedSlug}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            재검증 실행
          </button>

          <button
            onClick={handleApprove}
            disabled={busy || !val?.valid}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-emerald-600/20 cursor-pointer"
          >
            <ThumbsUp className="w-4 h-4" />
            발행 승인 (Approve)
          </button>
        </div>
      </div>

      {banner && (
        <div
          className={`p-4 rounded-xl border text-xs sm:text-sm flex items-center justify-between ${
            banner.type === 'ok'
              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-200'
              : 'bg-rose-950/60 border-rose-800 text-rose-200'
          }`}
        >
          <span>{banner.text}</span>
          {banner.type === 'ok' && selectedSlug && (
            <button
              onClick={() => onNavigate('publish', selectedSlug)}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer"
            >
              발행 센터로 이동
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {detail && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left 4 cols: Validation & Security Gate */}
          <div className="lg:col-span-4 space-y-4">
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  {val?.valid ? (
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                  )}
                  품질 및 프라이버시 검증 게이트
                </h2>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    val?.valid
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}
                >
                  {val?.valid ? 'PASS' : 'BLOCKED'}
                </span>
              </div>

              {val && (
                <div className="space-y-2">
                  {Object.entries(val.checks).map(([key, ok]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs"
                    >
                      <span className="text-slate-300">{CHECK_LABELS[key] || key}</span>
                      {ok ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> 통과
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                          <AlertTriangle className="w-3.5 h-3.5" /> 실패
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {val && val.errors.length > 0 && (
                <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-xs text-rose-200 space-y-1">
                  <div className="font-bold text-rose-300">차단 사유 (Errors):</div>
                  {val.errors.map((err, i) => (
                    <p key={i}>• {err}</p>
                  ))}
                </div>
              )}

              {val && val.warnings.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-950/50 border border-amber-800 text-xs text-amber-200 space-y-1">
                  <div className="font-bold text-amber-300">주의 항목 (Warnings):</div>
                  {val.warnings.map((w, i) => (
                    <p key={i}>• {w}</p>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2 text-xs">
              <h3 className="font-bold text-slate-100 text-sm">현재 게시물 상태 요약</h3>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">상태 (Stage)</span>
                <span className="font-mono text-indigo-300">{detail.summary.stage}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">원본 파일</span>
                <span className="font-mono text-slate-300">{detail.summary.raw_file || '-'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">초안 파일</span>
                <span className="font-mono text-slate-300">{detail.summary.draft_file || '-'}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">승인본 파일</span>
                <span className="font-mono text-emerald-300">
                  {detail.summary.approved_file || '(미승인)'}
                </span>
              </div>
            </div>
          </div>

          {/* Right 8 cols: Unified Diff & Rendered Markdown Preview */}
          <div className="lg:col-span-8 space-y-4">
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
              <h2 className="text-sm font-bold text-slate-100">
                Unified Diff (원문 <code className="text-amber-300">stories/raw</code> vs 편집본 <code className="text-indigo-300">stories/drafts</code>)
              </h2>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs max-h-80 overflow-y-auto space-y-0.5">
                {diffLines.map((line, idx) => {
                  let cls = 'text-slate-400';
                  if (line.startsWith('+') && !line.startsWith('+++')) {
                    cls = 'text-emerald-300 bg-emerald-950/30';
                  } else if (line.startsWith('-') && !line.startsWith('---')) {
                    cls = 'text-rose-300 bg-rose-950/30';
                  } else if (line.startsWith('@@')) {
                    cls = 'text-indigo-400';
                  }
                  return (
                    <div key={idx} className={`px-1.5 py-0.5 whitespace-pre-wrap ${cls}`}>
                      {line}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
              <h2 className="text-sm font-bold text-slate-100">
                최종 Hugo Markdown 전문 미리보기 (Front Matter 포함)
              </h2>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                {detail.draft_markdown}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
