import pandas as pd
import google.generativeai as genai
import json
import time
import re

# ── 설정 ──────────────────────────────────────────────
INPUT_CSV   = "joongna_002.csv"
OUTPUT_CSV  = "joongna_extracted_02.csv"

genai.configure(api_key="AIzaSyBwqjRNLisX4B24qIaDEgoofPYP3U_hnIw")  # ← API 키 입력
model = genai.GenerativeModel("gemini-2.5-flash")

BATCH_SIZE   = 10   # 한 번에 처리할 행 수 (토큰 여유 있으면 20까지 가능)
WAIT_BETWEEN = 13   # 요청 간격 (초) — 분당 5회 제한
MAX_RETRY    = 3


# ── 배치 분석 함수 ──────────────────────────────────────
def extract_batch(rows: list[dict]) -> list[dict]:
    """여러 행을 한 번에 Gemini에 보내고 JSON 배열로 받습니다."""

    items = ""
    for idx, r in enumerate(rows):
        items += f"""
[{idx}]
제목: {r['title']}
본문: {r['body']}
"""

    prompt = f"""아래 중고폰 판매 게시글 {len(rows)}개에서 각각 정보를 추출하세요.
반드시 JSON 배열로만 응답하고, 다른 텍스트는 절대 포함하지 마세요.

{items}

각 항목 추출 규칙:
- battery_pct  : 배터리 성능 숫자 (없으면 null)
- damage       : "yes"(기스/찍힘/파손) / "minor"(잔기스/미세) / "no"(무기스 명시) / null(언급없음)
- accessories  : "yes"(박스/충전기 등 포함) / "no"(기기만) / null(언급없음)

응답 형식 (JSON 배열만, 순서 유지):
[
  {{"battery_pct": 88, "damage": "minor", "accessories": "yes"}},
  {{"battery_pct": null, "damage": "yes", "accessories": "no"}}
]"""

    for attempt in range(MAX_RETRY):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            # 반환값이 배열인지 확인
            if isinstance(result, list) and len(result) == len(rows):
                return result
            raise ValueError(f"응답 개수 불일치: 요청 {len(rows)}개, 응답 {len(result)}개")

        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = 15
                match = re.search(r"seconds:\s*(\d+)", err)
                if match:
                    wait = int(match.group(1)) + 2
                print(f"  ⚠️  429 제한 — {wait}초 대기 후 재시도 ({attempt+1}/{MAX_RETRY})")
                time.sleep(wait)
            else:
                print(f"  ❌ 오류: {e}")
                raise

    # 재시도 모두 실패 시 null로 채움
    return [{"battery_pct": None, "damage": None, "accessories": None}] * len(rows)


# ── 메인 처리 ──────────────────────────────────────────
def main():
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    total = len(df)
    est_requests = (total + BATCH_SIZE - 1) // BATCH_SIZE
    est_minutes  = est_requests * WAIT_BETWEEN // 60

    print(f"총 {total}행 로드 완료")
    print(f"배치 크기 {BATCH_SIZE}행 → 요청 {est_requests}회 → 예상 소요: 약 {est_minutes}분\n")

    all_results = []
    rows_buffer = []
    index_buffer = []

    def flush(buffer_rows, buffer_idx):
        """buffer를 API에 보내고 결과를 all_results에 추가"""
        results = extract_batch(buffer_rows)
        for i, res in zip(buffer_idx, results):
            all_results.append((i, res))
        print(f"  ✅ [{buffer_idx[0]+1}~{buffer_idx[-1]+1}/{total}] 완료")
        time.sleep(WAIT_BETWEEN)

    for i, row in df.iterrows():
        title = str(row.get("제목", ""))
        body  = str(row.get("본문", ""))

        if len(body.strip()) < 5:
            all_results.append((i, {"battery_pct": None, "damage": None, "accessories": None}))
            continue

        rows_buffer.append({"title": title, "body": body})
        index_buffer.append(i)

        if len(rows_buffer) >= BATCH_SIZE:
            flush(rows_buffer, index_buffer)
            rows_buffer, index_buffer = [], []

    # 남은 것 처리
    if rows_buffer:
        flush(rows_buffer, index_buffer)

    # 결과 정렬 후 df에 병합
    all_results.sort(key=lambda x: x[0])
    result_df = pd.DataFrame([r for _, r in all_results])

    df["배터리성능(%)"] = result_df["battery_pct"].values
    df["손상여부"]      = result_df["damage"].values
    df["구성품포함"]    = result_df["accessories"].values

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 저장 완료: {OUTPUT_CSV}")
    print(df[["제목", "배터리성능(%)", "손상여부", "구성품포함"]].to_string())


if __name__ == "__main__":
    main()