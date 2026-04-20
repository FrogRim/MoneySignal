import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';

const fetchMock = vi.fn<typeof fetch>();

function mockJsonResponse(payload: unknown, ok = true): Response {
  return {
    ok,
    json: async () => payload,
  } as Response;
}

describe('App', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    window.MoneySignalHost = undefined;
  });

  it('renders feed items and opens detail with clear navigation', async () => {
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/session')) {
        return mockJsonResponse({ status: 'active' });
      }

      if (url.endsWith('/feed')) {
        return mockJsonResponse({
          items: [
            {
              id: 'sig_001',
              decision: 'briefing',
              title: '삼성전자 신호',
              asset: { symbol: '005930', name: '삼성전자', market: 'KR' },
              signal_strength: 'watch',
              summary: '거래량과 수급이 함께 붙었어요.',
              reasons: ['외국인 순매수 확대', '거래량 동반 상승'],
              risks: ['단기 변동성 확대'],
              watch_action: '장중 거래량이 유지되는지 보세요.',
              confidence: 0.76,
              published_at: '2026-04-19T09:00:00+00:00',
              agent_votes: [],
              evidence_refs: [],
            },
          ],
        });
      }

      if (url.endsWith('/signals/sig_001')) {
        return mockJsonResponse({
          signal: {
            id: 'sig_001',
            decision: 'briefing',
            title: '삼성전자 신호',
            asset: { symbol: '005930', name: '삼성전자', market: 'KR' },
            signal_strength: 'watch',
            summary: '거래량과 수급이 함께 붙었어요.',
            reasons: ['외국인 순매수 확대', '거래량 동반 상승'],
            risks: ['단기 변동성 확대'],
            watch_action: '장중 거래량이 유지되는지 보세요.',
            confidence: 0.76,
            published_at: '2026-04-19T09:00:00+00:00',
            agent_votes: [
              { agent: 'chart', stance: 'positive', confidence: 0.78 },
            ],
            evidence_refs: [
              { type: 'market_event', ref: 'evt_001' },
            ],
          },
        });
      }

      throw new Error(`unexpected fetch url: ${url}`);
    });

    render(<App />);

    expect(screen.getByText('오늘 신호를 불러오고 있어요.')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '신호 자세히 보기' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '닫기' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: '신호 자세히 보기' }));

    expect(await screen.findByRole('button', { name: '목록으로 돌아가기' })).toBeInTheDocument();
    expect(screen.getByText('왜 봐야 하나요')).toBeInTheDocument();
    expect(screen.getByText('리스크')).toBeInTheDocument();
    expect(screen.getByText('다음에 볼 포인트')).toBeInTheDocument();
    expect(screen.getByText('chart · positive · 0.78')).toBeInTheDocument();
  });

  it('renders a reassuring empty state when feed is empty', async () => {
    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ status: 'active' }))
      .mockResolvedValueOnce(mockJsonResponse({ items: [] }));

    render(<App />);

    expect(await screen.findByText('지금은 눈에 띄는 신호가 없어요.')).toBeInTheDocument();
    expect(
      screen.getByText('시장 흐름이 또렷해지면 여기에서 다시 정리해드릴게요.'),
    ).toBeInTheDocument();
  });

  it('renders retryable error state when feed loading fails', async () => {
    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ status: 'active' }))
      .mockRejectedValueOnce(new Error('network error'))
      .mockResolvedValueOnce(mockJsonResponse({ status: 'active' }))
      .mockResolvedValueOnce(
        mockJsonResponse({
          items: [
            {
              id: 'sig_002',
              decision: 'briefing',
              title: 'SK하이닉스 신호',
              asset: { symbol: '000660', name: 'SK하이닉스', market: 'KR' },
              signal_strength: 'watch',
              summary: '다시 불러오기에 성공했어요.',
              reasons: ['이유 1', '이유 2'],
              risks: ['리스크 1'],
              watch_action: '다시 확인해 보세요.',
              confidence: 0.73,
              published_at: '2026-04-19T09:10:00+00:00',
              agent_votes: [],
              evidence_refs: [],
            },
          ],
        }),
      );

    render(<App />);

    expect(await screen.findByText('신호를 아직 가져오지 못했어요.')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '다시 불러오기' }));

    await waitFor(() => {
      expect(screen.getByText('SK하이닉스 신호')).toBeInTheDocument();
    });
  });

  it('renders expired session guidance separately from generic errors', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ status: 'expired' }));

    render(<App />);

    expect(await screen.findByText('로그인 시간이 지나서 다시 들어와야 해요.')).toBeInTheDocument();
    expect(screen.getByText('토스에서 다시 열면 같은 서비스 흐름으로 이어서 볼 수 있어요.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '토스에서 다시 열기' })).toBeDisabled();
  });

  it('renders unauthenticated guidance separately from generic errors', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ status: 'unauthenticated' }));

    render(<App />);

    expect(await screen.findByText('토스 로그인 후에 신호를 볼 수 있어요.')).toBeInTheDocument();
    expect(screen.getByText('안전한 확인을 위해 토스에서 다시 시작해 주세요.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '토스 로그인으로 이동' })).toBeDisabled();
  });

  it('opens the help page from the feed and returns back safely', async () => {
    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ status: 'active' }))
      .mockResolvedValueOnce(mockJsonResponse({ items: [] }));

    render(<App />);

    expect(await screen.findByRole('button', { name: '서비스 안내' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '서비스 안내' }));

    expect(screen.getByText('서비스 안내')).toBeInTheDocument();
    expect(screen.getByText('이 앱은 신호를 이해하기 쉽게 정리해드려요.')).toBeInTheDocument();
    expect(screen.getByText('무엇을 하지 않나요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '홈으로 돌아가기' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '홈으로 돌아가기' }));

    expect(screen.getByText('지금 시장에서 다시 볼 신호만 간단히 정리했어요.')).toBeInTheDocument();
  });

  it('calls host close action when the host contract exists', async () => {
    const close = vi.fn();
    window.MoneySignalHost = { close };

    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ status: 'active' }))
      .mockResolvedValueOnce(mockJsonResponse({ items: [] }));

    render(<App />);

    await screen.findByText('지금은 눈에 띄는 신호가 없어요.');
    await userEvent.click(screen.getByRole('button', { name: '닫기' }));

    expect(close).toHaveBeenCalledTimes(1);
  });

  it('calls host re-entry action when session guidance is shown and host contract exists', async () => {
    const reenterSession = vi.fn();
    window.MoneySignalHost = { reenterSession };
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ status: 'expired' }));

    render(<App />);

    await screen.findByText('로그인 시간이 지나서 다시 들어와야 해요.');
    await userEvent.click(screen.getByRole('button', { name: '토스에서 다시 열기' }));

    expect(reenterSession).toHaveBeenCalledTimes(1);
  });
});
