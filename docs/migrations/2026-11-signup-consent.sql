-- 2026-11 회원가입 약관·개인정보 처리방침 동의 기록 (티켓 16b)
--
-- users 테이블에 동의 기록 컬럼 3개를 추가한다.
-- - 기존 계정은 동의 기록이 없으므로 모두 NULL 허용 (재동의 처리는 후속 티켓)
-- - IF NOT EXISTS 라서 여러 번 실행해도 안전하다 (PostgreSQL 9.6+)
-- - 기존 데이터는 수정하지 않는다
--
-- 실행 순서 (사람이 직접): 로컬(gopssl_dev) → 베타(gopssl_beta) → 운영(Supabase)
-- ⚠️ 반드시 이 SQL을 먼저 실행한 뒤 코드를 배포한다.
--    컬럼이 없는 DB에 새 코드가 올라가면 users 를 조회하는 모든 요청(로그인·인증 포함)이 500 이 된다.

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version   TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_version TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS agreed_at       TIMESTAMPTZ;

COMMIT;

-- 확인용 (선택):
-- SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--  WHERE table_name = 'users'
--    AND column_name IN ('terms_version', 'privacy_version', 'agreed_at');
