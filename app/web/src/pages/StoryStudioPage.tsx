import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  FilePlus2,
  Lock,
  Save,
  Sparkles,
  Wand2,
} from 'lucide-react';
import { NavTab } from '../App';
import { StoryDetail, StorySummary } from '../types';

interface Props {
  selectedSlug?: string;
  onSelectSlug: (slug: string) => void;
  onNavigate: (tab: NavTab, slug?: string) => void;
}

export const StoryStudioPage: React.FC<Props> = ({
  selectedSlug,
  onSelectSlug,
  onNavigate,
}) => {
  const [stories, setStories] = useState<StorySummary[]>([]);
  const [mode, setMode] = useState<'new' | 'edit'>(selectedSlug ? 'edit' : 'new');

  // New story form state
  const [rawInput, setRawInput] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [newTemplate, setNewTemplate] = useState('auto');
  const [newTags, setNewTags] = useState('');

  // Existing story edit state
  const [detail, setDetail] = useState<StoryDetail | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editCategory, setEditCategory] = useState('essay');
  const [editTags, setEditTags] = useState('');
  const [editBody, setEditBody] = useState('');

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const loadStoriesList = async () => {
    const res = await fetch('/api/blog/stories');
    const json = await res.json();
    setStories(json.items || []);
  };

  const loadStoryDetail = async (slug: string) => {
    try {
      const res = await fetch(`/api/blog/stories/${encodeURIComponent(slug)}`);
      if (!res.ok) return;
      const d: StoryDetail = await res.json();
      setDetail(d);
      setEditTitle(d.front_matter?.title || d.summary.title || '');
      setEditDescription(d.front_matter?.description || d.summary.description || '');
      const cats = d.front_matter?.categories || [];
      setEditCategory(cats[0] || d.summary.template || 'essay');
      setEditTags((d.front_matter?.tags || []).join(', '));
      setEditBody(d.body_markdown || '');
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStoriesList();
  }, []);

  useEffect(() => {
    if (selectedSlug && mode === 'edit') {
      loadStoryDetail(selectedSlug);
    }
  }, [selectedSlug, mode]);

  const handleCreateStoryAndDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawInput.trim() || rawInput.trim().length < 5) {
      setMessage({ type: 'err', text: '원문 스토리를 최소 5자 이상 입력해 주세요.' });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const tagsArr = newTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await fetch('/api/blog/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_text: rawInput,
          title: newTitle.trim() || null,
          slug: newSlug.trim() || null,
          template: newTemplate,
          tags: tagsArr.length > 0 ? tagsArr : null,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || '초안 생성 중 오류가 발생했습니다.');
      }
      const createdSlug = json.summary?.slug || json.slug;
      await loadStoriesList();
      onSelectSlug(createdSlug);
      setMode('edit');
      await loadStoryDetail(createdSlug);
      setMessage({
        type: 'ok',
        text: `원문 보존(stories/raw/${createdSlug}.md) 및 초안 생성이 완료되었습니다!`,
      });
    } catch (err: unknown) {
      setMessage({
        type: 'err',
        text: err instanceof Error ? err.message : '오류가 발생했습니다.',
      });
    } finally {
      setBusy(false);
    }
  };

  const handleSaveDraftEdits = async () => {
    if (!selectedSlug) return;
    setBusy(true);
    setMessage(null);
    try {
      const tagsArr = editTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await fetch(`/api/blog/stories/${encodeURIComponent(selectedSlug)}/draft`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle,
          description: editDescription,
          tags: tagsArr,
          category: editCategory,
          body_markdown: editBody,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || '초안 저장 실패');
      }
      setDetail(json);
      await loadStoriesList();
      setMessage({ type: 'ok', text: '편집본 초안 및 원문 대비 Diff 리포트가 업데이트되었습니다.' });
    } catch (err: unknown) {
      setMessage({
        type: 'err',
        text: err instanceof Error ? err.message : '초안 저장 중 오류가 발생했습니다.',
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <Wand2 className="w-5 h-5 text-indigo-400" />
            스토리 입력 &amp; AI 편집 초안 스튜디오
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            자유 형식의 메모·경험담·기술 노트를 입력하면 원문을 <code className="text-indigo-300">stories/raw/</code>에 안전하게 보존하고 Hugo 초안을 생성합니다.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => {
              setMode('new');
              setMessage(null);
            }}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium cursor-pointer ${
              mode === 'new'
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <FilePlus2 className="w-4 h-4" />
            새 스토리 입력
          </button>

          <select
            value={mode === 'edit' && selectedSlug ? selectedSlug : ''}
            onChange={(e) => {
              if (e.target.value) {
                onSelectSlug(e.target.value);
                setMode('edit');
                setMessage(null);
              }
            }}
            className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs sm:text-sm text-slate-200"
          >
            <option value="" disabled>
              기존 스토리 선택 ({stories.length}건)
            </option>
            {stories.map((s) => (
              <option key={s.slug} value={s.slug}>
                [{s.stage}] {s.title} ({s.slug})
              </option>
            ))}
          </select>
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl border text-xs sm:text-sm flex items-center justify-between ${
            message.type === 'ok'
              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-200'
              : 'bg-rose-950/60 border-rose-800 text-rose-200'
          }`}
        >
          <span>{message.text}</span>
          {selectedSlug && message.type === 'ok' && (
            <button
              onClick={() => onNavigate('review', selectedSlug)}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold cursor-pointer"
            >
              Diff 검토 및 승인 게이트로 이동
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {mode === 'new' ? (
        /* NEW STORY INPUT FORM */
        <form
          onSubmit={handleCreateStoryAndDraft}
          className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                글 제목 (비워두면 본문 첫 줄에서 자동 추출)
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="예: 주말에 로컬 블로그 자동화 파이프라인을 만든 이야기"
                className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                URL Slug (영문 소문자·하이픈 권장)
              </label>
              <input
                type="text"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="예: weekend-blog-automation"
                className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                글 성격 템플릿
              </label>
              <select
                value={newTemplate}
                onChange={(e) => setNewTemplate(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="auto">자동 추천 (Auto Detect)</option>
                <option value="essay">에세이 / 회고 (essay)</option>
                <option value="experience">경험 공유 (experience)</option>
                <option value="technical-note">기술 노트 (technical-note)</option>
                <option value="review">리뷰 / 후기 (review)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              태그 (쉼표로 구분, 비워두면 본문 키워드 기반 추천)
            </label>
            <input
              type="text"
              value={newTags}
              onChange={(e) => setNewTags(e.target.value)}
              placeholder="예: 회고, 자동화, Hugo, 개발노트"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-medium text-slate-300">
                자유 형식 스토리 / 메모 원문 (TXT / Markdown)
              </label>
              <span className="text-[11px] text-slate-400">
                코드 블록(```) 내부는 교정하지 않고 100% 보존합니다
              </span>
            </div>
            <textarea
              rows={14}
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder="떠오르는 생각, 프로젝트 경험, 기술 검토 메모를 자유롭게 적어주세요. 맞춤법이나 문단 정리는 편집 엔진이 초안에서 도와드리며, 원문은 stories/raw/에 그대로 보존됩니다."
              className="w-full p-4 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 font-mono leading-relaxed focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3">
            <button
              type="submit"
              disabled={busy}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold shadow-lg shadow-indigo-600/25 cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              {busy ? '초안 생성 중...' : '원본 보존 & 블로그 초안 생성'}
            </button>
          </div>
        </form>
      ) : (
        /* EXISTING STORY SIDE-BY-SIDE RAW & DRAFT EDITOR */
        detail && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left 5 cols: Read-only Raw Story & Editorial Summary */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-300">
                    <Lock className="w-3.5 h-3.5" />
                    원본 보존 파일 (Read-Only)
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {detail.summary.raw_file}
                  </span>
                </div>
                <pre className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 whitespace-pre-wrap font-mono max-h-96 overflow-y-auto leading-relaxed">
                  {detail.raw_content || '(원본 파일 없음)'}
                </pre>
              </div>

              {detail.review_report?.change_summary && (
                <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
                  <h3 className="text-sm font-bold text-slate-100">
                    AI 편집 요약 &amp; 제안 사항
                  </h3>
                  <div className="space-y-2 text-xs">
                    <div className="font-semibold text-indigo-300">교정 및 구조화 내역:</div>
                    <ul className="list-disc list-inside text-slate-300 space-y-1">
                      {detail.review_report.change_summary.grammar_and_structure.map((g, i) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>

                    {detail.review_report.change_summary.fact_check_items.length > 0 && (
                      <>
                        <div className="font-semibold text-amber-300 pt-2">[검증 필요] 사실 확인 항목:</div>
                        <ul className="list-disc list-inside text-amber-200 space-y-1">
                          {detail.review_report.change_summary.fact_check_items.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </>
                    )}

                    {detail.review_report.change_summary.suggestions.length > 0 && (
                      <>
                        <div className="font-semibold text-emerald-300 pt-2">편집자 참고 제안 (본문 미삽입):</div>
                        <ul className="list-disc list-inside text-slate-300 space-y-1">
                          {detail.review_report.change_summary.suggestions.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right 7 cols: Editable Draft Front Matter & Body */}
            <div className="lg:col-span-7 rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-100">
                  초안 편집기 (<code className="text-indigo-300">{detail.summary.draft_file}</code>)
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveDraftEdits}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer"
                  >
                    <Save className="w-3.5 h-3.5" />
                    초안 저장 &amp; Diff 갱신
                  </button>
                  <button
                    onClick={() => onNavigate('review', detail.summary.slug)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-indigo-700 bg-indigo-950/70 hover:bg-indigo-900 text-indigo-200 text-xs font-semibold cursor-pointer"
                  >
                    Diff 검토 &amp; 승인으로 이동
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs text-slate-400 mb-1">제목 (title)</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">카테고리/템플릿</label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100"
                  >
                    <option value="essay">essay</option>
                    <option value="experience">experience</option>
                    <option value="technical-note">technical-note</option>
                    <option value="review">review</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">요약 설명 (description)</label>
                  <input
                    type="text"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">태그 (쉼표 구분)</label>
                  <input
                    type="text"
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  본문 Markdown (Front Matter는 상단 입력값으로 자동 생성됩니다)
                </label>
                <textarea
                  rows={16}
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                  className="w-full p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs sm:text-sm font-mono text-slate-100 leading-relaxed"
                />
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
};
