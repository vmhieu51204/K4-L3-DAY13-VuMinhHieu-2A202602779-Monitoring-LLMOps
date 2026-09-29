# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Vũ Minh Hiếu
- **MSSV:** 2A202602779
- **Lớp:** K4-L3A
- **Repository URL:** `https://github.com/vmhieu51204/K4-L3-DAY13-VuMinhHieu-2A202602779-Monitoring-LLMOps`
- **Commit SHA cuối:** Commit SHA cuối cùng trên nhánh `main` khi push và nộp trên LMS/Codelabs
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602779`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 55/100 | 100/100 | Đạt toàn bộ tiêu chuẩn correlation ID, structlog metadata context và PII redaction |
| `validate_dashboard.py` | 0/6 | 6/6 | Khớp 100% schema và contract định nghĩa trong `config/dashboard.yaml` |
| `pytest` | 8 passed, 3 failed | 22 passed | Toàn bộ 22/22 unit và integration tests pass hoàn toàn |
| Số traces hợp lệ | 0 | ≥15 | Traces đầy đủ 3 cấp: root observation (`lab-agent-run`), `retrieval`, `generation` |
| Số PII leak | >10 | 0 | Không còn rò rỉ Email, SĐT VN, CCCD 12 số, Thẻ tín dụng 16 số |
| Latency P95 / TTFT P95 | ~160ms / ~55ms | ~165ms / ~52ms | Đạt mục tiêu SLO latency P95 (< 1500ms) |
| Retrieval success rate | 100% | 100% | Đạt mục tiêu SLO retrieval success (≥ 98%) |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `app/middleware.py`, middleware kiểm tra header `X-Request-ID`. Nếu request chưa có hoặc sai format, sinh mới theo định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). Sau đó gọi `clear_contextvars()` để xóa context cũ của request trước và gán `bind_contextvars(correlation_id=request_id)`. Header `X-Request-ID` cũng được set vào HTTP response header để client đối chiếu.
- **Các metadata được ghi vào structured log:** Mỗi log line dạng JSON chứa: `timestamp` (ISO-8601 UTC), `event`, `correlation_id`, `user_id_hash` (SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env` (environment từ `APP_ENV`), `latency_ms`, `status_code`, `path`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong structlog pipeline ngay trước JSON renderer / file writer. Processor này đệ quy duyệt qua mọi value trong event dict và áp dụng Regex để thay thế PII bằng placeholder (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_CCCD]`, `[REDACTED_CARD]`).
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt điểm tuyệt đối 100/100 (`submission/evidence/02-log-validator.txt`) và kiểm tra trực quan file `data/logs.jsonl` (`submission/evidence/04-structured-log.png` và `05-pii-redaction.png`).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Mọi trace đều được gửi tới project `day13-k4-l3a-2A202602779` trên Langfuse Cloud (`https://jp.cloud.langfuse.com`), với `user_id` băm gắn định danh `student-vuminhhieu`.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `agent`), ghi nhận thông tin request tổng thể, `correlation_id`, `user_id_hash`, tags.
  - Child 1: `retrieval` (type `retriever`), theo dõi query đã scrub PII, số lượng docs và latency tìm kiếm.
  - Child 2: `generation` (type `generation`), theo dõi model (`claude-sonnet-4-5`), prompt input, output tokens, cost details và prompt linkage.
- **Cách nối trace với log:** Cả structured log trong `data/logs.jsonl` và observation metadata trong Langfuse trace đều lưu chung một trường `correlation_id` (ví dụ `req-xxxx`). Khi có lỗi hoặc cảnh báo, chỉ cần copy `correlation_id` từ log để search trên Langfuse và ngược lại.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, labels: `baseline`, `production`
- **Version/label candidate:** Version 2, labels: `candidate`, `latest`
- **Trace ID của mỗi version:**
  - Trace dùng Baseline (v1, label `baseline`): `be94b60b94b3438e7d3e7bf097b9e19e` (`correlation_id`: `req-prompt-v1-baseline`)
  - Trace dùng Candidate (v2, label `candidate`): `e06a719df4414d1b8672633642f0b1f3` (`correlation_id`: `req-prompt-v2-candidate`)
  - Trace sau khi Promote v2 (v2, label `production`): `921a3dc9aa8371004bdef350be3fe1a2` (`correlation_id`: `req-prompt-v2-promoted`)
  - Trace sau khi Rollback v1 (v1, label `production`): `e1d55c264ea9d2ac1b2b27d9c8abc981` (`correlation_id`: `req-prompt-v1-rolledback`)
- **Cách promote và rollback `production`:**
  - Trong Langfuse, prompt version có tính bất biến (immutable). Việc quản lý triển khai dựa trên **Labels**:
  - **Promote:** Gán nhãn `production` từ Version 1 sang Version 2 thông qua Langfuse UI (hoặc `lf.update_prompt(name='day13-chat', version=2, new_labels=['candidate', 'production'])`). Ứng dụng runtime tự động nhận diện Version 2 khi truy vấn label `production`.
  - **Rollback:** Khi cần hoàn tác, di chuyển nhãn `production` quay trở lại Version 1 (`lf.update_prompt(name='day13-chat', version=1, new_labels=['baseline', 'production'])`). Ứng dụng ngay lập tức trở lại sử dụng Version 1 mà không cần sửa code hay redeploy.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Triển khai đúng contract tại `config/dashboard.yaml` và giao diện web tại `http://127.0.0.1:8000/dashboard`:
  1. `latency`: Line chart thể hiện Request Latency P95 và TTFT P95 (threshold 1500ms).
  2. `traffic`: Bar chart thể hiện Request Count (RPS) theo feature.
  3. `errors`: Line/Bar chart thể hiện Error Rate (%) và Retrieval Success Rate (%) (SLO 98%).
  4. `cost`: Cumulative chart thể hiện Total Cost USD và Cost per 1K requests.
  5. `tokens`: Line chart thể hiện Input vs Output tokens.
  6. `quality`: Line chart thể hiện Average Quality Score theo heuristic (threshold 0.70).
- **SLO và lý do chọn:**
  - Latency P95 ≤ 1500ms: Bảo đảm phản hồi nhanh cho trải nghiệm người dùng cuối trong interactive chat.
  - Error rate ≤ 1.0%: Bảo đảm độ tin cậy dịch vụ (99.0% availability).
  - Retrieval success rate ≥ 98.0%: Tránh việc LLM bị ảo giác (hallucination) do thiếu context văn bản.
- **Cách tính error budget:**
  - Với SLO 99% thành công trong chu kỳ 30 ngày (tương đương 100,000 requests):
  - Error Budget = `100% - 99% = 1%` tổng số request = `1,000 failed requests`.
  - Nếu trong 1 giờ có 50 requests bị lỗi, hệ thống đã tiêu thụ `50 / 1000 = 5%` error budget.
- **Ba alert và runbook tương ứng:**
  - Alert 1: `high_latency_p95` (P95 > 2000ms trong 5m) -> Runbook: Kiểm tra child spans của `retrieval` và `generation` trong trace, kiểm tra mạng hoặc model backend.
  - Alert 2: `high_error_rate` (Error rate > 5% trong 3m) -> Runbook: Kiểm tra log lỗi HTTP 5xx, kiểm tra service dependencies hoặc PII validator exception.
  - Alert 3: `low_quality_score` (Quality score < 0.60 trong 10m) -> Runbook: Kiểm tra retrieval relevance, rà soát prompt version gần nhất và rollback về baseline nếu cần.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-29 09:43:56 UTC – 09:44:10 UTC (tương ứng 16:43:56 – 16:44:10 Asia/Ho_Chi_Minh)
- **Triệu chứng từ metrics:** P95 Latency trên dashboard tăng vọt từ mức baseline ~165ms lên **2655ms** (đoạn load test concurrent 5 client latency ghi nhận từ 7991ms đến 13315ms), vi phạm nghiêm trọng SLO P95 (vượt quá ngưỡng cảnh báo 2000ms trong `config/challenge.json` và threshold 1500ms). Trong khi đó, TTFT P95 vẫn duy trì tốt (~50ms) và Error Rate = 0%, cho thấy sự cố thuộc dạng suy giảm hiệu năng do I/O blocking.
- **Log line và correlation ID liên quan:**
  - **Correlation ID:** `req-8a150cb0`
  - **Log line:**
    ```json
    {"service": "api", "latency_ms": 2655, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 90, "cost_usd": 0.001455, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "feature": "monitoring", "correlation_id": "req-8a150cb0", "model": "claude-sonnet-4-5", "user_id_hash": "ed72e61117f6", "session_id": "k4-l3a-challenge-s05", "env": "dev", "level": "info", "ts": "2026-09-29T09:43:58.999037Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - **Trace ID:** `f3f672c14c5d724600c44cce50a96d5e`
  - **Chi tiết waterfall các span:**
    - Root observation `lab-agent-run` (type `AGENT`, ID `81e3271725a96e10`): tổng thời gian **2.656s**
    - Child span `retrieval` (type `RETRIEVER`, ID `0d73bf98a646f761`): thời gian thực thi **2.501s** (chiếm tới **94.2%** tổng thời gian request)
    - Child span `generation` (type `GENERATION`, ID `f3759a339c442659`): thời gian thực thi chỉ **0.151s** (hoàn toàn bình thường)
  - **Span gây ảnh hưởng chính:** Span **`retrieval`**.
- **Root cause:** Module truy xuất tài liệu `retrieve()` (Vector Store / Retriever) bị suy giảm hiệu năng nghiêm trọng, gây trễ thêm 2.5 giây cho mỗi truy vấn RAG do nghẽn I/O blocking hoặc timeout mạng khi kết nối cơ sở dữ liệu vector.
- **Fix action:**
  - Vô hiệu hóa ngay lập tức cờ sự cố (`POST /incidents/rag_slow/disable`).
  - Áp dụng timeout nghiêm ngặt cho tầng retriever (ví dụ timeout 1.0s) kết hợp fallback tài liệu mặc định để bảo vệ SLO tổng thể của API.
  - Tích hợp caching layer (Redis / In-memory semantic cache) cho các truy vấn retrieval phổ biến nhằm giảm tải trực tiếp lên Vector Store.
- **Preventive measure:**
  - Thiết lập riêng SLO và cảnh báo Prometheus/Alertmanager cho tầng RAG: `retrieval_latency_p95 > 1000ms trong 3m` bắn thông báo vào kênh `#llmops-alerts`.
  - Tối ưu hóa vector index (HNSW/IVF index) trên vector database và triển khai health check định kỳ cho retriever worker.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định thực hiện PII redaction bằng Structlog processor trước bước serialize JSON. Điều này ngăn chặn triệt để nguy cơ PII rò rỉ vào log file, audit file, console stream mà không làm chậm luồng xử lý chính.
- **Một lỗi/blocker đã gặp:** Khi gọi tạo prompt nhiều lần từ script, Langfuse tự động tăng số version lên v3, v4 gây ra các prompt trùng lặp (duplicate) và gây hiểu nhầm về cơ chế rollback.
- **Cách tìm nguyên nhân và xử lý:** Tra cứu Langfuse Python SDK và phát hiện Langfuse quản lý rollback bằng Labels (`update_prompt(name, version, new_labels)`), không phải bằng cách clone version cũ. Đã sử dụng `lf.api.prompts.delete` để dọn sạch v3, v4 và cấu hình chính xác nhãn `production`/`baseline` cho v1 và `candidate` cho v2.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - Metrics (Dashboard) cho biết **"Khi nào và cái gì bị ảnh hưởng"** (triệu chứng diện rộng: spike latency, tăng error rate).
  - Logs cho biết **"Sự kiện gì xảy ra và request cụ thể nào bị lỗi"** thông qua `correlation_id` và error message.
  - Traces cho biết **"Tại sao lỗi xảy ra và điểm nghẽn nằm ở span cụ thể nào"** (waterfall visualization: retrieval chậm hay generation timeout).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Prompt versioning và labels tách biệt chu kỳ phát hành prompt khỏi chu kỳ release code backend, cho phép instant rollback khi prompt mới gây hallucination hoặc suy giảm chất lượng.
  - Theo dõi token & cost giúp phát hiện sớm hiện tượng prompt injection hoặc loop generation gây bùng nổ chi phí (cost spike).
  - SLO định lượng ranh giới an toàn cho hệ thống và cung cấp tiêu chuẩn khách quan để kích hoạt cảnh báo (alerts) trước khi người dùng phàn nàn.
- **Điều quan trọng nhất đã học:** Hiểu sâu sắc cách xây dựng hệ thống Full Observability cho ứng dụng GenAI bằng cách kết hợp nhịp nhàng giữa Structured Logging, Metrics Dashboard, và Distributed Tracing (Langfuse).
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Toàn bộ các checkpoint từ CP0 đến CP4 đã được thực hiện và kiểm chứng hoàn chỉnh, đáp ứng 100/100 log validator, 6/6 dashboard validator, 22/22 unit tests và phân tích chi tiết incident từ challenge chính thức.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
