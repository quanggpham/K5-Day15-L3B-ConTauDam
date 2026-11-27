-- Forward-only, expand step. Ghi quyết định duyệt + dòng audit trong CÙNG một transaction (một lời gọi RPC
-- của PostgREST = một transaction). CHƯA chạy thử trên Postgres/Supabase thật: cần chạy `supabase db reset`
-- ở môi trường test rồi thử các ca accept/reject/request_changes/edited/xung đột trước khi lên production.
--
-- Không DROP/TRUNCATE/DELETE. Cột mới nullable, không backfill (audit cũ để NULL = "chưa ghi nhận").
-- DOWN:
--   drop function public.review_recommendation(uuid, uuid, integer, text, text, text, uuid, text);
--   alter table public.recommendation_reviews drop constraint recommendation_reviews_status_before_check,
--     drop constraint recommendation_reviews_status_after_check, drop column status_before, drop column status_after;

-- 1) Audit trước/sau cho trạng thái duyệt (content_before/content_after đã có từ 000003).
--    ALTER TABLE không kích hoạt trigger append-only theo dòng; không sửa dòng audit cũ.
alter table public.recommendation_reviews
  add column status_before text,
  add column status_after text,
  add constraint recommendation_reviews_status_before_check check (status_before is null or status_before in
    ('pending','accepted','rejected','changes_requested','edited')),
  add constraint recommendation_reviews_status_after_check check (status_after is null or status_after in
    ('accepted','rejected','changes_requested','edited'));

-- 2) RPC duyệt. Gọi từ backend bằng service_role (bypass RLS). Backend đã kiểm owner; hàm kiểm lại owner
--    trong cùng transaction (phòng thủ nhiều lớp). actor = owner vì bản này chưa có chia sẻ.
--
-- Máy trạng thái (review_status NULL coi như 'pending'); PHẢI khớp REVIEW_TRANSITIONS ở
-- codebase/backend/api/run_repository.py (test đối chiếu từng dòng `when ... then p_decision = any (array[...])`):
--   pending           -> accept | reject | request_changes
--   accepted          -> reject | request_changes
--   rejected          -> accept | request_changes
--   changes_requested -> edited | reject        (không accept bản gốc sau khi đã yêu cầu sửa)
--   edited            -> accept | reject | request_changes | edited   (duyệt lại bản sửa tay)
--
-- Đồng thời: SELECT ... FOR UPDATE khoá dòng đề xuất; request thứ hai cùng version chờ khoá, đọc lại dòng mới
-- (READ COMMITTED) và thấy version đã tăng -> 'version_conflict'. UPDATE vẫn giữ điều kiện version = expected.
-- Trả jsonb {outcome: ok|replayed|not_found|version_conflict|invalid_transition|invalid_input, ...},
-- không raise cho lỗi nghiệp vụ để backend map mã HTTP ổn định.
--
-- Replay (retry sau timeout): CHỈ 'replayed' khi có dòng audit khớp (expected_version, actor, decision, comment,
-- content nếu edited) VÀ audit.new_version = version hiện tại của đề xuất (tức lần ghi đó chưa bị ghi đè). Ví dụ
-- v1 accept -> v2, reject@v2 -> v3, gửi lại accept@v1 -> 'version_conflict' (409), không phải 'replayed'.
--
-- Không trả nguyên dòng: recommendation/review chỉ gồm các trường allowlist (khớp RECOMMENDATION_FIELDS và
-- REVIEW_FIELDS ở run_repository.py; test đối chiếu). Không có actor_email trong kết quả.
create function public.review_recommendation(
  p_run_id uuid,
  p_recommendation_id uuid,
  p_expected_version integer,
  p_decision text,
  p_comment text,
  p_content text,
  p_actor_id uuid,
  p_actor_email text
) returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_rec public.recommendations%rowtype;
  v_review public.recommendation_reviews%rowtype;
  v_status text;
  v_new_status text;
  v_content_before text;
  v_allowed boolean;
  v_rec_json jsonb;
  v_review_json jsonb;
  v_edited boolean := coalesce(p_decision = 'edited', false);
begin
  if p_run_id is null or p_recommendation_id is null or p_actor_id is null
     or p_expected_version is null or p_expected_version < 1
     or p_decision is null or p_decision not in ('accept','reject','request_changes','edited')
     or (p_comment is not null and length(p_comment) > 2000)
     or (v_edited and (p_content is null or btrim(p_content) = '' or length(p_content) > 4000))
     or (not v_edited and p_content is not null) then
    return jsonb_build_object('outcome', 'invalid_input');
  end if;

  -- Owner của run (cùng phản hồi not_found cho "không tồn tại" và "không thuộc coach").
  perform 1 from public.analysis_runs r where r.id = p_run_id and r.user_id = p_actor_id;
  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;

  select * into v_rec from public.recommendations
   where id = p_recommendation_id and analysis_run_id = p_run_id
   for update;
  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;

  v_rec_json := jsonb_build_object(
      'id', v_rec.id, 'analysis_run_id', v_rec.analysis_run_id, 'kc_code', v_rec.kc_code,
      'priority', v_rec.priority, 'content', v_rec.content, 'citations', v_rec.citations, 'version', v_rec.version,
      'review_status', v_rec.review_status, 'is_edited', v_rec.is_edited, 'needs_rereview', v_rec.needs_rereview,
      'jev_score', v_rec.jev_score, 'updated_at', v_rec.updated_at);

  if v_rec.version <> p_expected_version then
    -- Gửi lại đúng request đã thành công (retry sau timeout) VÀ lần ghi đó còn là trạng thái hiện tại
    -- (new_version = version hiện tại) -> trả lại kết quả cũ, không ghi thêm. Bị ghi đè -> version_conflict.
    select * into v_review from public.recommendation_reviews rv
     where rv.recommendation_id = p_recommendation_id and rv.run_id = p_run_id
       and rv.expected_version = p_expected_version and rv.actor_id = p_actor_id
       and rv.decision = p_decision and rv.comment is not distinct from p_comment
       and (not v_edited or rv.content_after = p_content)
       and rv.new_version = v_rec.version
     order by rv.at desc, rv.id desc
     limit 1;
    if found then
      v_review_json := jsonb_build_object(
      'id', v_review.id, 'run_id', v_review.run_id, 'recommendation_id', v_review.recommendation_id,
      'expected_version', v_review.expected_version, 'new_version', v_review.new_version,
      'decision', v_review.decision, 'comment', v_review.comment, 'content_before', v_review.content_before,
      'content_after', v_review.content_after, 'needs_rereview', v_review.needs_rereview,
      'actor_id', v_review.actor_id, 'at', v_review.at, 'status_before', v_review.status_before,
      'status_after', v_review.status_after);
      return jsonb_build_object('outcome', 'replayed', 'recommendation', v_rec_json, 'review', v_review_json);
    end if;
    return jsonb_build_object('outcome', 'version_conflict', 'recommendation', v_rec_json);
  end if;

  v_status := coalesce(v_rec.review_status, 'pending');
  v_content_before := v_rec.content;
  v_allowed := case v_status
    when 'pending' then p_decision = any (array['accept','reject','request_changes'])
    when 'accepted' then p_decision = any (array['reject','request_changes'])
    when 'rejected' then p_decision = any (array['accept','request_changes'])
    when 'changes_requested' then p_decision = any (array['edited','reject'])
    when 'edited' then p_decision = any (array['accept','reject','request_changes','edited'])
    else false
  end;
  if not v_allowed then
    return jsonb_build_object('outcome', 'invalid_transition', 'recommendation', v_rec_json);
  end if;

  v_new_status := case p_decision
    when 'accept' then 'accepted'
    when 'reject' then 'rejected'
    when 'request_changes' then 'changes_requested'
    else 'edited'
  end;

  -- Bản sửa tay: is_edited/needs_rereview = true, jev_score = NULL (không thừa hưởng JEV của bản gốc).
  -- needs_rereview giữ true sau khi đã sửa (ràng buộc recommendations_edited_no_jev_check): nghĩa là
  -- "bản sửa chưa được kiểm định lại"; việc coach duyệt lại thể hiện ở review_status.
  update public.recommendations set
    version = version + 1,
    review_status = v_new_status,
    content = case when v_edited then p_content else content end,
    is_edited = is_edited or v_edited,
    needs_rereview = case when v_edited then true else needs_rereview end,
    jev_score = case when v_edited then null else jev_score end
  where id = p_recommendation_id and analysis_run_id = p_run_id and version = p_expected_version
  returning * into v_rec;
  if not found then  -- không xảy ra khi đã giữ khoá FOR UPDATE; giữ để không bao giờ ghi audit mồ côi
    return jsonb_build_object('outcome', 'version_conflict');
  end if;

  insert into public.recommendation_reviews (
    run_id, recommendation_id, expected_version, new_version, decision, comment,
    content_before, content_after, needs_rereview, actor_id, actor_email, status_before, status_after
  ) values (
    p_run_id, p_recommendation_id, p_expected_version, v_rec.version, p_decision, p_comment,
    v_content_before, v_rec.content, v_rec.needs_rereview, p_actor_id, p_actor_email, v_status, v_new_status
  )
  returning * into v_review;

  v_rec_json := jsonb_build_object(
      'id', v_rec.id, 'analysis_run_id', v_rec.analysis_run_id, 'kc_code', v_rec.kc_code,
      'priority', v_rec.priority, 'content', v_rec.content, 'citations', v_rec.citations, 'version', v_rec.version,
      'review_status', v_rec.review_status, 'is_edited', v_rec.is_edited, 'needs_rereview', v_rec.needs_rereview,
      'jev_score', v_rec.jev_score, 'updated_at', v_rec.updated_at);
  v_review_json := jsonb_build_object(
      'id', v_review.id, 'run_id', v_review.run_id, 'recommendation_id', v_review.recommendation_id,
      'expected_version', v_review.expected_version, 'new_version', v_review.new_version,
      'decision', v_review.decision, 'comment', v_review.comment, 'content_before', v_review.content_before,
      'content_after', v_review.content_after, 'needs_rereview', v_review.needs_rereview,
      'actor_id', v_review.actor_id, 'at', v_review.at, 'status_before', v_review.status_before,
      'status_after', v_review.status_after);
  return jsonb_build_object('outcome', 'ok', 'recommendation', v_rec_json, 'review', v_review_json);
end;
$$;

revoke execute on function public.review_recommendation(uuid, uuid, integer, text, text, text, uuid, text)
  from public, anon, authenticated;
grant execute on function public.review_recommendation(uuid, uuid, integer, text, text, text, uuid, text)
  to service_role;

notify pgrst, 'reload schema';
