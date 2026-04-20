import { useEffect, useMemo, useState } from 'react';

type SignalDecision = 'reject' | 'briefing' | 'instant_push';

type AssetView = {
  symbol: string;
  name: string;
  market: string;
};

type AgentVote = {
  agent: string;
  stance: string;
  confidence: number;
};

type EvidenceRef = {
  type: string;
  ref: string;
};

type SignalDetail = {
  id: string;
  decision: SignalDecision;
  title: string;
  asset: AssetView;
  signal_strength: string;
  summary: string;
  reasons: string[];
  risks: string[];
  watch_action: string;
  confidence: number;
  published_at: string;
  agent_votes: AgentVote[];
  evidence_refs: EvidenceRef[];
};

type FeedResponse = {
  items: SignalDetail[];
};

type SignalResponse = {
  signal: SignalDetail;
};

type SessionStatus = 'active' | 'expired' | 'unauthenticated';

type SessionResponse = {
  status: SessionStatus;
};

type FeedStatus = 'loading' | 'ready' | 'empty' | 'error';

type MoneySignalHost = {
  close?: () => void;
  reenterSession?: () => void;
};

declare global {
  interface Window {
    MoneySignalHost?: MoneySignalHost;
  }
}

type ViewState =
  | { page: 'feed' }
  | { page: 'detail'; signalId: string }
  | { page: 'help' };

const apiBaseUrl = import.meta.env.VITE_PIPELINE_BASE_URL ?? '';

function formatConfidencePercent(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

function getHost(): MoneySignalHost | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.MoneySignalHost ?? null;
}

export function App() {
  const host = useMemo(() => getHost(), []);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('active');
  const [feedStatus, setFeedStatus] = useState<FeedStatus>('loading');
  const [feedItems, setFeedItems] = useState<SignalDetail[]>([]);
  const [feedError, setFeedError] = useState('');
  const [detailSignal, setDetailSignal] = useState<SignalDetail | null>(null);
  const [detailError, setDetailError] = useState('');
  const [viewState, setViewState] = useState<ViewState>({ page: 'feed' });

  useEffect(() => {
    void loadFeedPage();
  }, []);

  useEffect(() => {
    if (viewState.page !== 'detail') {
      setDetailSignal(null);
      setDetailError('');
      return;
    }

    void loadSignal(viewState.signalId);
  }, [viewState]);

  const headerTitle = useMemo(() => {
    if (viewState.page === 'detail' && detailSignal !== null) {
      return detailSignal.asset.name;
    }

    if (viewState.page === 'help') {
      return '서비스 안내';
    }

    return 'MoneySignal';
  }, [detailSignal, viewState.page]);

  async function loadFeedPage() {
    setFeedStatus('loading');
    setFeedError('');

    try {
      const sessionResponse = await fetch(`${apiBaseUrl}/session`);
      if (!sessionResponse.ok) {
        throw new Error('session request failed');
      }

      const sessionPayload = (await sessionResponse.json()) as SessionResponse;
      setSessionStatus(sessionPayload.status);
      if (sessionPayload.status !== 'active') {
        setFeedItems([]);
        return;
      }

      const feedResponse = await fetch(`${apiBaseUrl}/feed`);
      if (!feedResponse.ok) {
        throw new Error('feed request failed');
      }

      const feedPayload = (await feedResponse.json()) as FeedResponse;
      setFeedItems(feedPayload.items);
      setFeedStatus(feedPayload.items.length === 0 ? 'empty' : 'ready');
    } catch {
      setSessionStatus('active');
      setFeedItems([]);
      setFeedStatus('error');
      setFeedError('신호를 아직 가져오지 못했어요.');
    }
  }

  async function loadSignal(signalId: string) {
    setDetailSignal(null);
    setDetailError('');

    try {
      const response = await fetch(`${apiBaseUrl}/signals/${signalId}`);
      if (!response.ok) {
        throw new Error('detail request failed');
      }

      const payload = (await response.json()) as SignalResponse;
      setDetailSignal(payload.signal);
    } catch {
      setDetailError('상세 신호를 아직 열지 못했어요. 목록에서 다시 시도해 주세요.');
    }
  }

  return (
    <main className="app-shell">
      <div className="app-frame">
        <header className="top-bar" aria-label="상단 네비게이션">
          <div className="top-bar__left">
            {viewState.page === 'detail' ? (
              <button
                className="nav-button"
                type="button"
                onClick={() => setViewState({ page: 'feed' })}
              >
                목록으로 돌아가기
              </button>
            ) : viewState.page === 'help' ? (
              <button
                className="nav-button"
                type="button"
                onClick={() => setViewState({ page: 'feed' })}
              >
                홈으로 돌아가기
              </button>
            ) : null}
          </div>
          <strong>{headerTitle}</strong>
          <button
            className="close-button"
            type="button"
            disabled={host?.close === undefined}
            onClick={() => host?.close?.()}
          >
            닫기
          </button>
        </header>

        {viewState.page === 'feed' ? (
          <>
            <section className="panel hero">
              <p className="eyebrow">초보 투자자를 위한 오늘의 관찰 포인트</p>
              <h1 className="title">지금 시장에서 다시 볼 신호만 간단히 정리했어요.</h1>
              <p className="description">
                매수 지시 대신, 왜 중요하고 무엇을 더 보면 되는지부터 보여드려요.
              </p>
              <div className="hero-actions">
                <button
                  className="help-button"
                  type="button"
                  onClick={() => setViewState({ page: 'help' })}
                >
                  서비스 안내
                </button>
              </div>
            </section>
            {sessionStatus === 'expired'
              ? renderSessionState({
                  title: '로그인 시간이 지나서 다시 들어와야 해요.',
                  description: '토스에서 다시 열면 같은 서비스 흐름으로 이어서 볼 수 있어요.',
                  actionLabel: '토스에서 다시 열기',
                  onAction: host?.reenterSession,
                })
              : sessionStatus === 'unauthenticated'
                ? renderSessionState({
                    title: '토스 로그인 후에 신호를 볼 수 있어요.',
                    description: '안전한 확인을 위해 토스에서 다시 시작해 주세요.',
                    actionLabel: '토스 로그인으로 이동',
                    onAction: host?.reenterSession,
                  })
                : renderFeed({
                    feedError,
                    feedItems,
                    feedStatus,
                    onOpenDetail: (signalId) => setViewState({ page: 'detail', signalId }),
                    onRetry: () => {
                      void loadFeedPage();
                    },
                  })}
          </>
        ) : viewState.page === 'help' ? (
          renderHelp()
        ) : (
          renderDetail({ detailError, detailSignal })
        )}
      </div>
    </main>
  );
}

type FeedSectionProps = {
  feedStatus: FeedStatus;
  feedItems: SignalDetail[];
  feedError: string;
  onRetry: () => void;
  onOpenDetail: (signalId: string) => void;
};

function renderFeed(props: FeedSectionProps) {
  if (props.feedStatus === 'loading') {
    return (
      <section className="state-card" aria-live="polite">
        <strong>오늘 신호를 불러오고 있어요.</strong>
        <p className="description">조금만 기다리면 지금 볼 만한 흐름을 바로 보여드릴게요.</p>
      </section>
    );
  }

  if (props.feedStatus === 'error') {
    return (
      <section className="state-card" aria-live="assertive">
        <strong>{props.feedError}</strong>
        <p className="description">연결이 다시 잡히면 같은 화면에서 바로 이어서 볼 수 있어요.</p>
        <button className="retry-button" type="button" onClick={props.onRetry}>
          다시 불러오기
        </button>
      </section>
    );
  }

  if (props.feedStatus === 'empty') {
    return (
      <section className="state-card" aria-live="polite">
        <strong>지금은 눈에 띄는 신호가 없어요.</strong>
        <p className="description">시장 흐름이 또렷해지면 여기에서 다시 정리해드릴게요.</p>
      </section>
    );
  }

  return (
    <ul className="feed-list" aria-label="신호 목록">
      {props.feedItems.map((item) => (
        <li key={item.id} className="feed-item">
          <div className="feed-item__header">
            <strong>{item.title}</strong>
            <span className="feed-item__meta">
              {item.asset.name} · {item.asset.symbol} · 신뢰도: {formatConfidencePercent(item.confidence)}
            </span>
          </div>
          <p className="feed-item__summary">{item.summary}</p>
          <button
            className="detail-button"
            type="button"
            onClick={() => props.onOpenDetail(item.id)}
          >
            신호 자세히 보기
          </button>
        </li>
      ))}
    </ul>
  );
}

type SessionStateProps = {
  title: string;
  description: string;
  actionLabel: string;
  onAction?: () => void;
};

function renderSessionState(props: SessionStateProps) {
  return (
    <section className="state-card" aria-live="polite">
      <strong>{props.title}</strong>
      <p className="description">{props.description}</p>
      <button
        className="retry-button"
        type="button"
        disabled={props.onAction === undefined}
        onClick={() => props.onAction?.()}
      >
        {props.actionLabel}
      </button>
    </section>
  );
}

function renderHelp() {
  return (
    <section className="panel section-list">
      <div>
        <p className="eyebrow">MoneySignal을 사용하는 방법</p>
        <h1 className="title">이 앱은 신호를 이해하기 쉽게 정리해드려요.</h1>
        <p className="description">
          오늘 바로 거래하라는 뜻이 아니라, 지금 왜 다시 볼 만한지와 다음에 무엇을 확인하면 되는지를 짧게 보여드려요.
        </p>
      </div>

      <div>
        <h2>무엇을 볼 수 있나요</h2>
        <ul className="bullet-list">
          <li>지금 다시 볼 만한 신호 목록</li>
          <li>왜 중요한지에 대한 이유와 리스크</li>
          <li>다음에 확인할 관찰 포인트</li>
        </ul>
      </div>

      <div>
        <h2>무엇을 하지 않나요</h2>
        <ul className="bullet-list">
          <li>직접적인 매수·매도 지시를 하지 않아요.</li>
          <li>과장된 수익 약속이나 긴급한 행동을 유도하지 않아요.</li>
        </ul>
      </div>
    </section>
  );
}

type DetailSectionProps = {
  detailSignal: SignalDetail | null;
  detailError: string;
};

function renderDetail(props: DetailSectionProps) {
  if (props.detailError.length > 0) {
    return (
      <section className="state-card" aria-live="assertive">
        <strong>{props.detailError}</strong>
      </section>
    );
  }

  if (props.detailSignal === null) {
    return (
      <section className="state-card" aria-live="polite">
        <strong>상세 신호를 준비하고 있어요.</strong>
      </section>
    );
  }

  return (
    <section className="panel section-list">
      <div>
        <p className="eyebrow">{props.detailSignal.asset.market} · {props.detailSignal.asset.symbol}</p>
        <h1 className="title">{props.detailSignal.title}</h1>
        <p className="description">{props.detailSignal.summary}</p>
      </div>

      <div>
        <h2>왜 봐야 하나요</h2>
        <ul className="bullet-list">
          {props.detailSignal.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      <div>
        <h2>리스크</h2>
        <ul className="bullet-list">
          {props.detailSignal.risks.map((risk) => (
            <li key={risk}>{risk}</li>
          ))}
        </ul>
      </div>

      <div>
        <h2>다음에 볼 포인트</h2>
        <p className="description">{props.detailSignal.watch_action}</p>
      </div>

      <div>
        <h2>판단 근거</h2>
        <div className="metric-row">
          <span className="badge">신뢰도: {formatConfidencePercent(props.detailSignal.confidence)}</span>
          {props.detailSignal.agent_votes.map((vote) => (
            <span key={`${vote.agent}-${vote.stance}`} className="badge">
              {vote.agent} · {vote.stance} · {formatConfidencePercent(vote.confidence)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
