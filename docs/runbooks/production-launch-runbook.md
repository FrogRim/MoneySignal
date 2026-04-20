# MoneySignal 출시 런북

## 목적

이 문서는 MoneySignal을 앱인토스 검수 직후 실제 출시 단계로 가져갈 때 필요한 preflight, first-hour check, monitoring, rollback 절차를 정리합니다.

## 출시 전 preflight

### 문서 / 승인
- [ ] 검수 체크리스트 최신화
- [ ] reviewer walkthrough와 실제 앱 동선 일치 확인
- [ ] 루트 README / 서비스 README / 스펙 / ADR 최신 상태 확인
- [ ] launch owner와 first-hour monitor 담당자 지정

### 환경
- [ ] review / staging / production 환경 변수 매트릭스 정리
- [ ] Toss origin / host allowlist 정리
- [ ] Brain boundary 설정 확인
- [ ] Pipeline read API endpoint 확인
- [ ] Miniapp 빌드 산출물 확인
- [ ] `docker compose up -d --build` 기준 배포 절차 확인
- [ ] `app.<domain>` / `api.<domain>` host routing 확인

권장 기준:
- review/staging: `PIPELINE_ENV=demo`, `PIPELINE_SESSION_STATUS=active`
- production: `PIPELINE_ENV=production`, `/internal/rebuild-feed`는 내부 토큰 필수
- miniapp: 각 환경마다 `VITE_PIPELINE_BASE_URL`을 명시적으로 분리
- Brain은 public direct port를 열지 않고 Compose 내부 네트워크로만 둠
- 세부 값은 `./review-staging-env-matrix.md`, 배포 절차는 `./digitalocean-compose-deploy.md`에서 함께 관리

### 서비스 단위 확인
#### Brain
- [ ] `/health` 정상 응답
- [ ] `POST /v1/signals/evaluate` success/error smoke
- [ ] request ID / security headers / structured error 확인

#### Pipeline
- [ ] fixture replay 또는 candidate generation 정상 확인
- [ ] `/feed`, `/signals/{id}` smoke
- [ ] Brain 호출 실패 시 운영 추적 가능 여부 확인

#### Miniapp
- [ ] 홈/상세/빈 상태/에러 상태 확인
- [ ] 뒤로가기/닫기 확인
- [ ] 즉시 팝업 없음 확인
- [ ] 라이트 모드만 노출 확인

## 출시 직후 first-hour 체크

### 0~10분
- [ ] Brain `/health` 확인
- [ ] Pipeline `/feed` 응답 확인
- [ ] Miniapp 첫 진입 smoke
- [ ] 대표 상세 화면 smoke

### 10~30분
- [ ] 5xx 비율 확인
- [ ] p95 / p99 latency 확인
- [ ] `error.code` 분포 확인
- [ ] request ID 기반 추적이 가능한지 확인

### 30~60분
- [ ] 실제/테스트 사용자 피드백 채널 확인
- [ ] empty/error/session-expired 상태가 예상대로 동작하는지 확인
- [ ] 운영 담당자가 런북만 보고 대응 가능한지 재확인

## 모니터링 항목

### Brain
- `/health` availability
- `POST /v1/signals/evaluate` error rate
- `422`, `429`, `503`, `500` 비율
- `error.code` 세부 분포
- latency (p50 / p95 / p99)

### Pipeline
- candidate generation 성공률
- Brain evaluate 호출 성공률
- read API latency
- feed 생성 지연

### Miniapp
- 첫 화면 로드 성공 여부
- 상세 화면 로드 실패율
- session-expired UX 진입 빈도

## rollback trigger

아래 상황이면 즉시 rollback 또는 launch hold를 검토합니다.

- Brain 5xx 비율이 baseline 대비 급격히 상승
- Pipeline이 feed를 안정적으로 생성하지 못함
- Miniapp 홈 또는 상세가 열리지 않음
- 검수 가정과 다른 UX가 production에서 드러남
- Toss origin/host 정책 문제로 주요 요청이 실패함

## rollback 절차

### 1. Miniapp 노출 중단 또는 이전 안정 버전으로 복귀
- 현재 배포 아티팩트를 내리고 이전 안정 버전으로 전환
- review/production 환경에서 다시 홈/상세 smoke 수행

### 2. Pipeline rollback
- read model 생성 이전 안정 버전으로 전환
- `/feed`, `/signals/{id}` smoke 재확인

### 3. Brain rollback
- 마지막 안정 배포로 복귀
- `/health`, evaluate smoke 재확인

### 4. 커뮤니케이션
- 내부 채널에 rollback 이유 공유
- 재현 조건, 영향 범위, 다음 조치 기록

## 출시 성공 기준
- first-hour 동안 핵심 동선이 유지된다.
- 5xx / latency / `error.code`가 허용 범위 내에 있다.
- 운영자가 request ID를 기반으로 문제를 추적할 수 있다.
- 사용자가 앱 목적과 핵심 화면을 혼란 없이 사용할 수 있다.

## 출시 후 후속 작업
- review 과정에서 받은 수정 요청 반영 여부 정리
- v1 범위에서 미룬 항목(Toss Pay / IAP, 고급 개인화 등) 재평가
- 실제 사용자 행동 기반으로 브리핑/상세 UX 개선 포인트 정리
