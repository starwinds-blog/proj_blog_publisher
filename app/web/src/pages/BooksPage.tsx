import React, { useEffect, useState } from 'react';
import type { NavTab } from '../App';
import type { StorySummary } from '../types';

interface Book { slug: string; title: string; description: string; chapters: string[] }
interface Preview { items: Book[]; excluded: { book: string; chapter: string }[]; dry_run: boolean }
const field = 'w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-slate-100';
const button = 'rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed';

async function request<T>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const response = await fetch(`/api/blog/${path}`, body === undefined ? undefined : {
    method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력값을 확인해 주세요. URL 식별자는 영문 소문자·숫자·하이픈만 사용할 수 있습니다.');
  return data;
}

export const BooksPage: React.FC<{ onNavigate: (tab: NavTab, slug?: string) => void }> = ({ onNavigate }) => {
  const [books, setBooks] = useState<Book[]>([]);
  const [stories, setStories] = useState<StorySummary[]>([]);
  const [selected, setSelected] = useState(0);
  const [query, setQuery] = useState('');
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const book = books[selected];
  const storyMap = new Map(stories.map(story => [story.slug, story]));

  const load = async () => {
    setBusy(true); setError('');
    try {
      const [data, catalog] = await Promise.all([
        request<{ items: Book[] }>('books'), request<{ items: StorySummary[] }>('stories'),
      ]);
      setBooks(data.items); setStories(catalog.items); setLoaded(true);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const change = (next: Book[]) => { setBooks(next); setDirty(true); setPreview(null); setMessage(''); };
  const edit = (patch: Partial<Book>) => change(books.map((value, index) => index === selected ? { ...value, ...patch } : value));
  const move = (index: number, offset: number) => {
    const chapters = [...book.chapters];
    [chapters[index], chapters[index + offset]] = [chapters[index + offset], chapters[index]];
    edit({ chapters });
  };
  const save = async () => {
    setBusy(true); setError('');
    try {
      const data = await request<{ items: Book[] }>('books', { items: books }, 'PUT');
      setBooks(data.items); setDirty(false); setMessage('Books 구성을 로컬에 저장했습니다.');
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };
  const stage = async (approve: boolean) => {
    setBusy(true); setError('');
    try {
      const result = await request<Preview>('books/stage', { approve, dry_run: !approve });
      setPreview(result);
      setMessage(approve ? '승인한 Books 구성을 Hugo에 반영했습니다. 발행 센터에서 게시물 Publish를 승인하면 함께 배포됩니다.' : '공개될 책과 목차를 확인한 뒤 승인하세요.');
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  return <div className="space-y-6">
    <div><h1 className="text-2xl font-bold">Books · 주제별 묶음</h1>
      <p className="text-slate-400 mt-2">여러 글을 한 권의 책처럼 구성하세요. 같은 글을 여러 책에 담고 읽는 순서를 정할 수 있습니다.</p>
      <p className="text-sm text-slate-400 mt-1">로컬 저장 → 공개 목차 미리보기 → 승인하여 Hugo 반영 → 발행 센터에서 Publish</p>
    </div>
    {error && <div role="alert" className="text-rose-300">{error} {!loaded && <button className={button} onClick={load}>다시 불러오기</button>}</div>}
    {message && <p role="status" className="text-indigo-300">{message}</p>}
    {busy && <p role="status">처리 중...</p>}
    <fieldset disabled={busy || !loaded} className="space-y-6">
      <div className="flex flex-wrap gap-3 items-center">
        <button className={button} onClick={() => {
          let n = books.length + 1;
          while (books.some(item => item.slug === `book-${n}`)) n++;
          change([...books, { slug: `book-${n}`, title: '새 책', description: '', chapters: [] }]); setSelected(books.length);
        }}>+ 새 책</button>
        <button className={button} disabled={!dirty} onClick={save}>구성 저장{dirty ? ' *' : ''}</button>
        <button className={button} disabled={dirty} onClick={() => stage(false)}>공개 목차 미리보기 (Dry-run)</button>
        {dirty && <span className="text-sm text-amber-300">저장하지 않은 변경 사항이 있습니다. 다른 메뉴로 이동하기 전에 저장하세요.</span>}
      </div>
      <div className="grid lg:grid-cols-[260px_1fr] gap-6">
        <aside className="space-y-3" aria-label="책 목록">
          {books.length === 0 && <p className="text-slate-400">첫 책을 만들고 주제에 맞는 글을 담아보세요.</p>}
          {books.map((item, index) => <button key={index} aria-pressed={selected === index} onClick={() => setSelected(index)} className={`w-full text-left rounded-xl border p-4 ${selected === index ? 'border-indigo-500 bg-indigo-950/50' : 'border-slate-700 bg-slate-900'}`}>
            <strong className="block">{item.title || '제목 없음'}</strong><span className="text-sm text-slate-400">{item.chapters.length} chapters · /books/#{item.slug}</span>
          </button>)}
        </aside>
        {book && <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <label className="block">책 제목<input className={field} maxLength={120} value={book.title} onChange={e => edit({ title: e.target.value })} /></label>
          <label className="block">URL 식별자<input className={field} maxLength={80} value={book.slug} onChange={e => edit({ slug: e.target.value })} /><span className="text-xs text-slate-400">영문 소문자, 숫자, 하이픈 · 공개 주소: /books/#{book.slug}</span></label>
          <label className="block">책 소개<textarea className={field} maxLength={1000} value={book.description} onChange={e => edit({ description: e.target.value })} /></label>
          <h2 className="font-semibold">목차 · 읽는 순서</h2>
          {!book.chapters.length && <p className="text-slate-400">아래 글 목록에서 챕터를 추가하세요.</p>}
          <ol className="space-y-2">{book.chapters.map((slug, index) => <li key={slug} className="flex flex-wrap items-center gap-2 border border-slate-700 p-3 rounded-lg">
            <span className="flex-1">{index + 1}. {storyMap.get(slug)?.title || slug} <small className="text-slate-400">({storyMap.get(slug)?.stage || '글 없음'})</small></span>
            <button className={button} aria-label={`${index + 1}번 챕터 위로`} disabled={index === 0} onClick={() => move(index, -1)}>↑</button>
            <button className={button} aria-label={`${index + 1}번 챕터 아래로`} disabled={index === book.chapters.length - 1} onClick={() => move(index, 1)}>↓</button>
            <button className={button} onClick={() => edit({ chapters: book.chapters.filter(value => value !== slug) })}>제외</button>
          </li>)}</ol>
          <label className="block">추가할 글 검색<input className={field} placeholder="제목 또는 slug" value={query} onChange={e => setQuery(e.target.value)} /></label>
          <div className="max-h-64 overflow-y-auto space-y-2">{stories.filter(story => !book.chapters.includes(story.slug) && `${story.title} ${story.slug}`.toLowerCase().includes(query.toLowerCase())).map(story => <div key={story.slug} className="flex gap-3 items-center">
            <span className="flex-1">{story.title} <small className="text-slate-400">({story.stage})</small></span>
            <button className={button} onClick={() => edit({ chapters: [...book.chapters, story.slug] })}>추가</button>
          </div>)}</div>
          <p className="text-sm text-slate-400">초안도 구성에 담을 수 있지만, 공개 목차에는 Hugo에 반영된 글만 포함됩니다. 글을 발행한 뒤 Books 공개 목차도 다시 반영하세요.</p>
          <button className={`${button} text-rose-300`} onClick={() => { if (window.confirm(`“${book.title}” 책을 삭제할까요? 글 원본은 유지됩니다.`)) { change(books.filter((_, i) => i !== selected)); setSelected(0); } }}>책 삭제</button>
        </section>}
      </div>
      {preview && <section className="border border-indigo-800 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-semibold">공개 목차 {preview.dry_run ? '미리보기' : '반영 완료'}</h2>
        {!preview.items.length && <p>공개 가능한 챕터가 없어 Books 목록이 비어 있습니다.</p>}
        {preview.items.map(item => <div key={item.slug}><h3 className="font-semibold">{item.title}</h3><p className="text-slate-400">{item.description}</p><ol className="list-decimal pl-6">{item.chapters.map(slug => <li key={slug}>{storyMap.get(slug)?.title || slug}</li>)}</ol></div>)}
        {preview.excluded.length > 0 && <div className="text-amber-300"><p>공개 제외: {preview.excluded.length}개 챕터 (사이트 미반영)</p>{preview.excluded.map(item => <p key={`${item.book}/${item.chapter}`}>{item.book} / {storyMap.get(item.chapter)?.title || item.chapter}</p>)}</div>}
        {preview.dry_run && <button className={`${button} bg-indigo-600`} onClick={() => stage(true)}>이 공개 구성을 승인하여 Hugo에 반영</button>}
        {!preview.dry_run && <button className={button} onClick={() => onNavigate('publish')}>발행 센터로 이동</button>}
      </section>}
    </fieldset>
  </div>;
};
