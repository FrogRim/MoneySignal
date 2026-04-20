# MoneySignal DigitalOcean + Docker Compose 배포 런북

## 목적

이 문서는 MoneySignal을 1인 운영 기준으로 DigitalOcean Droplet 한 대에 배포하는 기본 절차를 정리합니다. 목표는 miniapp / pipeline / brain / reverse proxy를 한 번에 올리되, Brain은 public internet에 직접 노출하지 않는 것입니다.

## 배포 토폴로지

- `app.<domain>` → miniapp 정적 컨테이너
- `api.<domain>` → Pipeline API
- `brain` → Compose 내부 네트워크 전용 FastAPI 컨테이너
- `caddy` → host 기반 reverse proxy
- `pipeline_data` volume → feed store 영속화

기본 내부 호출:
- miniapp build arg: `MINIAPP_PIPELINE_BASE_URL=http://api.localhost:8080`
- Pipeline → Brain: `PIPELINE_BRAIN_BASE_URL=http://brain:8000`

## 저장소 산출물

- 루트 `docker-compose.yml`
- 루트 `.env.example`
- `infra/caddy/Caddyfile`
- `apps/toss-miniapp/Dockerfile`
- `apps/toss-miniapp/nginx.conf`
- `services/pipeline/Dockerfile`
- `services/brain/Dockerfile`

## 사전 준비

### 1. DigitalOcean 리소스
- Ubuntu Droplet 1대
- 연결할 도메인 1개 이상
- `app.<domain>`, `api.<domain>` DNS 레코드

### 2. 서버 기본 패키지
Droplet에서 아래를 준비합니다.

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
```

Docker / Compose plugin은 사용자 환경에 맞는 공식 설치 절차를 따릅니다.

### 3. 애플리케이션 배치

```bash
git clone <repo>
cd MoneySignal
cp .env.example .env
```

## `.env`에서 먼저 채울 값

최소 필수값:

- `MINIAPP_HOST=app.<domain>`
- `PIPELINE_HOST=api.<domain>`
- `MINIAPP_PIPELINE_BASE_URL=https://api.<domain>`
- `PIPELINE_INTERNAL_REBUILD_TOKEN=<strong-random-token>`
- `BRAIN_TRUSTED_HOSTS=brain,api.<domain>`

권장값:

- production: `PIPELINE_ENV=production`
- production: `PIPELINE_FEED_STORE_PATH=/data/feed-store.json`
- production direct browser access가 아니라면 `BRAIN_CORS_ALLOW_ORIGINS`는 비워 둠

## 배포 절차

### 1. 이미지 빌드 및 기동

```bash
docker compose up -d --build
```

### 2. 상태 확인

```bash
docker compose ps
docker compose logs caddy --tail=100
docker compose logs pipeline --tail=100
docker compose logs brain --tail=100
```

### 3. smoke check

```bash
curl -H "Host: api.<domain>" http://127.0.0.1:8080/session
curl -H "Host: api.<domain>" http://127.0.0.1:8080/feed
curl -H "Host: app.<domain>" http://127.0.0.1:8080/
```

production에서는 rebuild endpoint를 내부 토큰으로만 호출합니다.

```bash
curl -X POST \
  -H "Host: api.<domain>" \
  -H "x-pipeline-internal-token: <token>" \
  http://127.0.0.1:8080/internal/rebuild-feed
```

## 운영 원칙

- Brain은 `docker-compose.yml`에서 host port를 열지 않습니다.
- public 진입점은 Caddy만 둡니다.
- miniapp은 build 시점에 Pipeline URL을 주입합니다.
- feed store는 `pipeline_data` volume으로 유지합니다.
- review/staging/prod 값은 `review-staging-env-matrix.md`와 함께 관리합니다.

## review / staging 운영 팁

- review/staging은 `PIPELINE_ENV=demo`로 시작 가능
- walkthrough 직전 `POST /internal/rebuild-feed`로 deterministic fixture 재생성
- 세션 상태 리허설 시에만 `PIPELINE_SESSION_STATUS`를 `expired` 또는 `unauthenticated`로 변경

## 제한 사항

이 저장소의 현재 세션에서는 Docker CLI가 없어 `docker compose` 실제 기동 검증을 수행하지 못했습니다. Droplet 또는 Docker가 설치된 로컬 환경에서 아래를 반드시 확인해야 합니다.

- `docker compose up -d --build` 성공
- `app.<domain>` / `api.<domain>` host routing 정상 동작
- Pipeline → Brain 내부 호출 정상
- `pipeline_data` 재시작 후 유지 확인

## 후속 작업

- 실제 Toss host bridge / 로그인 경계 연결
- review/staging/prod 실 URL을 환경 매트릭스에 반영
- first-hour monitoring과 rollback rehearsal 수행
