# MoneySignal review / staging 환경 매트릭스

## 목적

이 문서는 Apps in Toss 제출 직전 필요한 review, staging, production 환경 값을 한 곳에서 고정하기 위한 기준 문서입니다. 실제 제출 전에 비어 있는 값은 반드시 채워야 하며, reviewer walkthrough는 이 문서를 기준으로 실행합니다.

## 환경별 기준

| 구분 | review | staging | production |
|---|---|---|---|
| `VITE_PIPELINE_BASE_URL` | review용 Pipeline URL | staging용 Pipeline URL | production용 Pipeline URL |
| `PIPELINE_ENV` | `demo` | `development` 또는 `demo` | `production` |
| `PIPELINE_SESSION_STATUS` | `active` | `active` | 실제 Toss 세션 연동 |
| `PIPELINE_BRAIN_BASE_URL` | review용 Brain URL 또는 비움 | staging용 Brain URL | production용 Brain URL |
| `PIPELINE_FEED_STORE_PATH` | review 전용 경로 | staging 전용 경로 | production 전용 경로 |
| `/internal/rebuild-feed` | 토큰 없이 허용 | 토큰 없이 허용 가능 | 내부 토큰 필수 |
| Brain trusted hosts / origins | review host만 허용 | staging host만 허용 | production host만 허용 |
| Toss 로그인 경로 | reviewer용 테스트 계정 또는 진입 경로 | staging용 진입 경로 | 실제 사용자 진입 경로 |
| Host bridge (`MoneySignalHost`) | review embedding host 기준 | staging embedding host 기준 | production Toss host 기준 |

## review 환경 고정값

review 제출 리허설 기준으로 아래를 권장합니다.

- `PIPELINE_ENV=demo`
- `PIPELINE_SESSION_STATUS=active`
- fixture replay 직후 `/feed`, `/signals/{id}` smoke 수행
- miniapp은 review 전용 `VITE_PIPELINE_BASE_URL`만 바라보게 빌드
- Brain 직접 노출이 아니라면 review host만 allowlist에 포함

## 시나리오별 임시 전환값

### 세션 만료 리허설
- `PIPELINE_SESSION_STATUS=expired`
- 확인 후 다시 `active`로 복귀

### 미인증 리허설
- `PIPELINE_SESSION_STATUS=unauthenticated`
- 확인 후 다시 `active`로 복귀

### empty state 리허설
- empty fixture로 rebuild 하거나 review store를 비운 뒤 `/feed` 재확인

### error state 리허설
- Pipeline API 연결 실패를 의도적으로 만들거나 staging 전용 실패 시나리오로 `다시 불러오기` 동작 확인

## 제출 전 반드시 채워야 하는 값

- [ ] review miniapp URL
- [ ] review Pipeline URL
- [ ] review Brain URL
- [ ] reviewer용 Toss 로그인 경로 또는 테스트 계정
- [ ] staging miniapp URL
- [ ] staging Pipeline URL
- [ ] production miniapp URL
- [ ] production Pipeline URL
- [ ] production Brain URL
- [ ] Brain trusted hosts / origins 실제 값

## 운영 원칙

- review와 production feed store는 분리합니다.
- review walkthrough 직전 feed를 deterministic fixture 기준으로 재생성합니다.
- production에서 `/internal/rebuild-feed`는 내부 토큰 없이 열지 않습니다.
- DigitalOcean Compose 배포에서는 `app.<domain>`과 `api.<domain>`를 Caddy host routing으로 분리합니다.
- Brain은 public internet에 직접 노출하지 않고 `PIPELINE_BRAIN_BASE_URL=http://brain:8000` 같은 내부 주소를 사용합니다.
- environment 값이 바뀌면 `review-submission-runbook.md`, `production-launch-runbook.md`, `digitalocean-compose-deploy.md`와 함께 갱신합니다.
