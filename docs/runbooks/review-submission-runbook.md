# MoneySignal 리뷰 제출 런북

## 목적

이 문서는 MoneySignal Apps in Toss miniapp을 검수 제출하기 전에 무엇을 준비하고, 어떤 순서로 리허설하고, 리뷰어에게 어떤 흐름을 안내할지 정리한 런북입니다.

## 제출 전 준비물

### 문서
- 루트 `README.md`
- Apps in Toss MVP 문서: `../product/apps-in-toss-mvp.md`
- 검수 체크리스트: `../product/review-checklist.md`
- 시스템 아키텍처 ADR: `../adrs/ADR-001-apps-in-toss-system-architecture.md`
- `../../services/brain/README.md`
- `../../services/pipeline/README.md`
- `../../apps/toss-miniapp/README.md`

### 환경
- review URL 또는 staging URL
- Pipeline base URL
- Brain base URL
- 테스트 계정 또는 리뷰용 Toss 로그인 경로
- 고정 fixture 또는 deterministic 테스트 데이터
- reviewer가 볼 대표 시나리오 3개
- 환경값 기준 문서: `./review-staging-env-matrix.md`

### review / staging 환경 매트릭스

| 항목 | review/staging 권장값 | 비고 |
|---|---|---|
| Miniapp `VITE_PIPELINE_BASE_URL` | review용 Pipeline URL | miniapp이 직접 읽는 API |
| Pipeline `PIPELINE_ENV` | `demo` | 내부 rebuild를 토큰 없이 허용 |
| Pipeline `PIPELINE_BRAIN_BASE_URL` | review용 Brain URL 또는 비워 둠 | 비우면 fixture stubbed Brain 사용 |
| Pipeline `PIPELINE_SESSION_STATUS` | `active` | 기본 walkthrough 값 |
| Pipeline `PIPELINE_FEED_STORE_PATH` | review 전용 경로 | demo/prod store 분리 |
| Brain host/origin allowlist | review host만 허용 | direct 호출이 아니라면 더 닫아도 됨 |

### 대표 시나리오
1. 홈에서 브리핑 목록 확인
2. 목록에서 상세 진입 후 이유/리스크/다음 포인트 확인
3. 도움말 진입 후 홈 복귀
4. 세션 만료 또는 미인증 상태 확인
5. 뒤로가기/닫기 경로 확인

## 제출 전 체크

- [ ] 홈 첫 진입에 즉시 팝업/바텀시트가 없다.
- [ ] 라이트 모드만 노출된다.
- [ ] CTA가 목적을 분명히 설명한다.
- [ ] 뒤로가기/닫기 경로가 모든 핵심 화면에서 명확하다.
- [ ] Toss 로그인 외 다른 로그인 경로가 없다.
- [ ] 에러 상태에서 내부 예외가 노출되지 않는다.
- [ ] 번들 크기와 주요 화면 로드 성능을 확인했다.
- [ ] 브레인/파이프라인/미니앱 문서가 현재 구현과 맞다.

## 내부 리허설 순서

### 1. 기술 리허설
- Brain health check 확인
- Pipeline read API 확인
- Miniapp 빌드 및 staging 접속 확인
- 요청 추적(request ID)과 에러 로그가 운영에서 식별 가능한지 확인

### 2. 제품 리허설
- 비개발자도 홈 화면만 보고 앱 목적을 이해하는지 확인
- 상세에서 이유/리스크/다음 행동이 자연스럽게 읽히는지 확인
- 빈 상태와 에러 상태가 실패처럼 느껴지지 않는지 확인

### 3. 검수 리허설
- reviewer walkthrough 문서만 보고 전체 흐름이 재현 가능한지 확인
- 테스트 계정/테스트 데이터가 문서와 일치하는지 확인
- 앱인토스 제약 위반 요소가 없는지 다시 체크

## reviewer walkthrough

### 사전 세팅
1. Pipeline review 환경에서 `POST /internal/rebuild-feed`를 호출해 fixture 기반 feed를 재생성합니다.
2. `PIPELINE_SESSION_STATUS=active`로 시작합니다.
3. miniapp이 review용 `VITE_PIPELINE_BASE_URL`을 읽는지 확인합니다.

### Flow 1: 기본 사용 흐름
1. 앱 진입
2. 홈 hero에서 앱 목적이 바로 이해되는지 확인
3. `신호 자세히 보기` 버튼으로 상세 진입
4. 이유, 리스크, 다음에 볼 포인트, confidence / agent vote 확인
5. `목록으로 돌아가기`로 홈 복귀

### Flow 2: 도움말 / 서비스 설명
1. 홈에서 `서비스 안내` 선택
2. 서비스 목적, 무엇을 보여주는지, 무엇을 하지 않는지 확인
3. `홈으로 돌아가기`로 복귀

### Flow 3: 데이터가 없는 경우
1. review 환경의 feed를 비우거나 empty fixture로 재생성
2. `지금은 눈에 띄는 신호가 없어요.` 상태와 안내 문구 확인

### Flow 4: 예외 / 세션 상태
1. API 오류를 유도해 `신호를 아직 가져오지 못했어요.`와 `다시 불러오기` 확인
2. `PIPELINE_SESSION_STATUS=expired`로 변경 후 `토스에서 다시 열기` 확인
3. `PIPELINE_SESSION_STATUS=unauthenticated`로 변경 후 `토스 로그인으로 이동` 확인
4. host bridge가 없는 review 환경에서는 관련 CTA가 disabled인지 확인

## 제출 직전 확인 질문
- 리뷰어가 앱의 목적을 1분 안에 이해할 수 있는가?
- 홈 → 상세 → 이탈 흐름이 자연스러운가?
- 검수자가 문제 삼을 만한 UX 패턴(즉시 팝업, 모호한 CTA, 닫기 부재)이 없는가?
- 문서 없이도 운영자가 문제를 재현하고 원인을 추적할 수 있는가?

## 제출 후 대응 준비
- 문의 대응 담당자 지정
- 재현 가능한 테스트 데이터 유지
- 수정 요청이 들어왔을 때 어떤 문서와 어떤 화면을 먼저 볼지 내부 합의
