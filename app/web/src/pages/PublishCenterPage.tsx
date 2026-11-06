import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  ExternalLink,
  FolderCheck,
  Globe,
  Play,
  RefreshCw,
  Rocket,
  Save,
  Settings,
  ShieldAlert,
  Terminal,
} from 'lucide-react';
import { PublishingConfig, StoryDetail, StorySummary } from '../types';

interface Props {
  selectedSlug?: string;
  onSelectSlug: (slug: string) => void;
}

export const PublishCenterPage: React.FC<Props> = ({ selectedSlug, onSelectSlug }) => {
  const [stories, setStories] = useState<StorySummary[]>([]);
  const [detail, setDetail] = useState<StoryDetail | null>(null);
  const [config, setConfig] = useState<PublishingConfig | null>(null);

  const [confirmPublicPush, setConfirmPublicPush] = useState(false);
  const [upsertMode, setUpsertMode] = useState(true);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([
    '발행 콘솔 대기 중... Dry-run 시뮬레이션 또는 로컬 스테이징/원격 배포를 선택하세요.',
  ]);
  const [busy, setBusy] = useState(false);
  const [settingsMsg, setSettingsMsg] = useState<string | null>(null);

  const loadAll = async () => {
    const [stRes, cfgRes] = await Promise.all([
      fetch('/api/blog/stories'),
      fetch('/api/blog/settings/publishing'),
    ]);
    const stJson = await stRes.json();
    const list: StorySummary[] = stJson.items || [];
    setStories(list);
    if (!selectedSlug && list.length > 0) {
      onSelectSlug(list[0].slug);
    }
    if (cfgRes.ok) {
      setConfig(await cfgRes.json());
    }
  };

  const loadDetail = async (slug: string) => {
    const res = await fetch(`/api/blog/stories/${encodeURIComponent(slug)}`);
    if (res.ok) {
      setDetail(await res.json());
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (selectedSlug) {
      loadDetail(selectedSlug);
    }
  }, [selectedSlug]);

  const executePublishAction = async (opts: {
    approve: boolean;
    dry_run: boolean;
    publish_remote: boolean;
  }) => {
    if (!selectedSlug) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/blog/stories/${encodeURIComponent(selectedSlug)}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approve: opts.approve,
          dry_run: opts.dry_run,
          upsert: upsertMode,
          publish_remote: opts.publish_remote,
          confirm_public_push: confirmPublicPush,
        }),
      });
      const json = await res.json();
      const lines: string[] = [
        `>>> 실행 시각: ${new Date().toLocaleTimeString()} | 대상: ${selectedSlug}`,
        ...(json.logs || []),
      ];
      if (!json.ok) {
        lines.push(`[ERROR] ${json.error || '실행 실패'}`);
      } else {
        lines.push(`[OK] 결과 상태: ${json.status} | 예상 URL: ${json.expected_url || '-'}`);
      }
      setConsoleLogs(lines);
      await loadAll();
      await loadDetail(selectedSlug);
    } finally {
      setBusy(false);
    }
  };

  const handleCheckRemoteStatus = async () => {
    if (!selectedSlug) return;
    setBusy(true);
    try {
      const res = await fetch(
        `/api/blog/publications/status?slug=${encodeURIComponent(selectedSlug)}&check_remote=true`
      );
      const json = await res.json();
      const rec = json.results?.[selectedSlug];
      setConsoleLogs([
        `>>> 원격 배포 및 URL 상태 조회 (${selectedSlug})`,
        JSON.stringify(rec, null, 2),
      ]);
      await loadAll();
      await loadDetail(selectedSlug);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setBusy(true);
    setSettingsMsg(null);
    try {
      const res = await fetch('/api/blog/settings/publishing', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        setConfig(await res.json());
        setSettingsMsg('배포 설정이 config/publishing.yaml 및 site/hugo.toml에 반영되었습니다.');
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <Rocket className="w-5 h-5 text-indigo-400" />
            Hugo + GitHub Pages 발행 센터
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Allowlist 기반 <code className="text-indigo-300">site/content/posts/</code> 반영, Dry-run 시뮬레이션, 명시적 승인 후 원격 Git Push 및 배포 상태 추적을 수행합니다.
          </p>
        </div>

        <select
          value={selectedSlug || ''}
          onChange={(e) => onSelectSlug(e.target.value)}
          className="px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs sm:text-sm text-slate-200"
        >
          {stories.map((s) => (
            <option key={s.slug} value={s.slug}>
              [{s.stage}] {s.title} ({s.slug})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 cols: Publish Controls & Execution Console */}
        <div className="lg:col-span-7 space-y-5">
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <FolderCheck className="w-4 h-4 text-emerald-400" />
              단계별 안전 발행 컨트롤러 ({selectedSlug})
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <label className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={upsertMode}
                  onChange={(e) => setUpsertMode(e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span className="text-slate-300">
                  동일 slug 존재 시 수정 발행 허용 (<code className="text-indigo-300">--upsert</code>)
                </span>
              </label>

              <label className="flex items-center gap-2.5 p-3 rounded-xl bg-amber-950/30 border border-amber-800/60 cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmPublicPush}
                  onChange={(e) => setConfirmPublicPush(e.target.checked)}
                  className="rounded border-amber-700"
                />
                <span className="text-amber-200 font-medium">
                  [필수 게이트] 공개 GitHub 저장소 원격 Push를 명시적으로 승인합니다
                </span>
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                onClick={() =>
                  executePublishAction({ approve: true, dry_run: true, publish_remote: false })
                }
                disabled={busy || !selectedSlug}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm font-medium text-slate-100 cursor-pointer"
              >
                <Play className="w-4 h-4 text-sky-400" />
                1단계: 승인 &amp; Dry-Run 시뮬레이션
              </button>

              <button
                onClick={() =>
                  executePublishAction({ approve: true, dry_run: false, publish_remote: false })
                }
                disabled={busy || !selectedSlug}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs sm:text-sm font-semibold text-white cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4" />
                2단계: 승인 &amp; 로컬 Hugo 사이트 반영 (Stage)
              </button>

              <button
                onClick={() =>
                  executePublishAction({ approve: true, dry_run: false, publish_remote: true })
                }
                disabled={busy || !selectedSlug || !confirmPublicPush}
                title={!confirmPublicPush ? '상단의 공개 GitHub Push 승인 체크박스를 먼저 선택하세요.' : ''}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 cursor-pointer"
              >
                <Rocket className="w-4 h-4" />
                3단계: GitHub 원격 Push &amp; 배포 실행
              </button>

              <button
                onClick={handleCheckRemoteStatus}
                disabled={busy || !selectedSlug}
                className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-700 bg-slate-950 hover:bg-slate-800 text-xs text-slate-300 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Actions / URL 배포 상태 확인
              </button>
            </div>
          </div>

          {/* Terminal Output */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                파이프라인 실행 콘솔 출력
              </h3>
              <span className="text-xs font-mono text-slate-400">scripts/prepare_publish.py</span>
            </div>
            <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-300 whitespace-pre-wrap max-h-72 overflow-y-auto leading-relaxed">
              {consoleLogs.join('\n')}
            </pre>
          </div>

          {/* Current Record Info */}
          {detail?.publication_record && (
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2 text-xs">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Globe className="w-4 h-4 text-indigo-400" />
                발행 이력 레코드 (<code className="text-indigo-300">stories/records/publications.json</code>)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 block">현재 상태</span>
                  <span className="font-mono font-semibold text-indigo-300">
                    {String(detail.publication_record.status || '-')}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 block">반영된 사이트 파일</span>
                  <span className="font-mono text-slate-200">
                    {String(detail.publication_record.site_file || '(미반영)')}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 sm:col-span-2 flex items-center justify-between">
                  <div>
                    <span className="text-slate-400 block">예상/실제 게시글 URL</span>
                    <span className="font-mono text-emerald-300">
                      {String(detail.publication_record.url || '-')}
                    </span>
                  </div>
                  {Boolean(detail.publication_record.url) && (
                    <a
                      href={String(detail.publication_record.url)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
                    >
                      열기 <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right 5 cols: Publishing & Repository Configuration */}
        <div className="lg:col-span-5 space-y-5">
          {config && (
            <form
              onSubmit={handleSaveConfig}
              className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Settings className="w-4 h-4 text-indigo-400" />
                  블로그 &amp; GitHub Pages 설정
                </h2>
                <button
                  type="submit"
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  설정 저장
                </button>
              </div>

              {settingsMsg && (
                <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800 text-xs text-emerald-200">
                  {settingsMsg}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">블로그 제목 (site_title)</label>
                  <input
                    type="text"
                    value={config.site_title}
                    onChange={(e) => setConfig({ ...config, site_title: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">블로그 소개 (site_description)</label>
                  <input
                    type="text"
                    value={config.site_description}
                    onChange={(e) => setConfig({ ...config, site_description: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1">GitHub Username / Owner</label>
                    <input
                      type="text"
                      value={config.github_owner}
                      onChange={(e) => setConfig({ ...config, github_owner: e.target.value })}
                      placeholder="예: my-username"
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">GitHub 공개 저장소 이름</label>
                    <input
                      type="text"
                      value={config.github_repo}
                      onChange={(e) => setConfig({ ...config, github_repo: e.target.value })}
                      placeholder="예: my-username.github.io"
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-100"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1">저장소 유형 (repo_type)</label>
                    <select
                      value={config.repo_type}
                      onChange={(e) => setConfig({ ...config, repo_type: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100"
                    >
                      <option value="user">User Site (&lt;user&gt;.github.io)</option>
                      <option value="project">Project Site (&lt;user&gt;.github.io/&lt;repo&gt;)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">배포 브랜치 (branch)</label>
                    <input
                      type="text"
                      value={config.branch}
                      onChange={(e) => setConfig({ ...config, branch: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-100"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">사이트 Base URL</label>
                  <input
                    type="text"
                    value={config.base_url}
                    onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
                    placeholder="https://<username>.github.io/"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-100"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 space-y-1.5">
                <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-amber-400" />
                  공개 저장소 안전 가드레일 안내
                </div>
                <p>
                  • <code className="text-slate-300">stories/raw/</code>(원문) 및 <code className="text-slate-300">stories/drafts/</code>(초안)는 절대 공개 Hugo 디렉토리(<code className="text-slate-300">site/</code>)로 복사되지 않습니다.
                </p>
                <p>
                  • GitHub CLI(<code className="text-slate-300">gh</code>) 없이도 표준 <code className="text-slate-300">git push</code>와 GitHub REST API(<code className="text-slate-300">urllib</code>)를 통해 배포 및 상태 확인이 수행됩니다.
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
