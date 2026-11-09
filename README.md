# Lab: Xây dựng Status Investigation Agent

Bạn sẽ tự viết một agent loop bằng Python. Agent dùng dữ liệu thật từ GitHub Status và Cloudflare Status để hỗ trợ điều tra sự cố, sau đó bạn dùng trace và eval để kiểm tra cách agent hoạt động.

**Mục tiêu:** gọi LLM → thực thi tool → đưa kết quả trở lại LLM → lặp đến khi trả lời hoặc hết giới hạn. Thời lượng dự kiến: **4 giờ**, gồm nghỉ 10 phút. Toàn bộ các bước trong [GUIDE.md](GUIDE.md) là nội dung của lab. Đọc thêm [RUBRIC.md](RUBRIC.md) để biết tiêu chí đánh giá.

## Lộ trình học

1. Khám phá status tools và tự code agent loop.
2. Thêm xử lý lỗi, giới hạn bước và trace.
3. Chạy hai bộ eval: case cơ bản E1–E6 và case nâng cao A1–A8.
4. Phân tích partial failure, prompt injection, nguồn và giới hạn dữ liệu; implement bước kiểm tra nguồn trong agent.
5. Chạy tests, đánh giá kết quả và trình bày trace của agent.

Các bước trên là một lab thống nhất. Timeline, yêu cầu và tiêu chí hoàn thành được mô tả trong [GUIDE.md](GUIDE.md).

## 1. Chuẩn bị

- Python **3.10+**, có Internet và API key của **một** trong bốn provider.
- Chọn model có hỗ trợ **tool calling**. API provider/model có thể phát sinh chi phí.
- Không cần cài package: project dùng Python standard library.

Mở terminal tại thư mục `labs/` đã clone hoặc tải về:

```bash
python3 --version
export PROVIDER=openai
export MODEL='<tên-model-có-tool-calling>'
export OPENAI_API_KEY='<api-key>'
```

Chọn cấu hình khác nếu cần:

| `PROVIDER` | Biến chứa key | `MODEL` |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | Tên model OpenAI bạn được cấp quyền dùng. |
| `gemini` | `GEMINI_API_KEY` | Tên model Gemini hỗ trợ function calling. |
| `removed-provider` | `removed-provider_API_KEY` | Tên model removed-model hỗ trợ tool use. |
| `openrouter` | `OPENROUTER_API_KEY` | Model ID đầy đủ trên OpenRouter, thường có dạng `provider/model`. |

Ví dụ chuyển sang Gemini: `export PROVIDER=gemini`, đặt `GEMINI_API_KEY` và `MODEL` phù hợp. Chọn một provider; không cần cả bốn key. File `.env.example` chỉ là mẫu: chương trình **không tự đọc `.env`**. Không commit key hay trace chứa dữ liệu nhạy cảm.

Adapter dùng Chat Completions cho OpenAI, Gemini compatibility và OpenRouter; removed-provider dùng Messages API. Nó phục vụ **tool calling cơ bản**, không bao phủ mọi tính năng đặc thù model như extended thinking. Khi provider từ chối model hoặc hết quota, kiểm tra quyền truy cập, model ID và key. Xem tài liệu: [OpenAI](https://developers.openai.com/api/docs/guides/function-calling), [Gemini](https://ai.google.dev/gemini-api/docs/openai), [removed-provider](https://platform.removed-model.com/docs/en/agents-and-tools/tool-use/how-tool-use-works), [OpenRouter](https://openrouter.ai/docs/guides/features/tool-calling).

## 2. Chạy thử

Sau khi hoàn thiện `agent.py`:

```bash
python3 run.py 'GitHub Actions hiện có sự cố không? Hãy kiểm tra incident gần đây.'
python3 run.py --mode live 'Cloudflare có incident liên quan cache purge không?'
python3 -m unittest discover -s tests -v
python3 evals/run_evals.py --case E2 --output eval_results_e2.json
python3 evals/run_evals.py --output eval_results_basic.json
python3 evals/run_evals.py --suite advanced --output eval_results_advanced.json
```

- Mặc định là `snapshot`: đọc dữ liệu được lưu sẵn; vẫn cần LLM API key.
- `live`: gọi status API thật, dữ liệu thay đổi và cần Internet. Cloudflare khuyến nghị User-Agent có thông tin liên hệ; giảng viên có thể đặt `export STATUS_USER_AGENT="StatusAgentLab/1.0 (contact: email-lop@example.edu)"` bằng thông tin liên hệ thực của lớp.
- Unit tests dùng fake provider, không cần key. **Ban đầu một số tests thất bại** vì `agent.py` chưa được implement.
- Eval gọi LLM thật, tiêu tốn token. Bắt đầu với một case; đọc output và tự chấm theo rubric. `manual_score: null` nghĩa là **chưa chấm**, không phải pass.
- Có thể override bằng `--provider`, `--model`, `--max-steps`. `--max-steps` là số lần gọi model, mặc định 6.

Snapshot là dữ liệu public được lưu ngày 09/11/2026. Không dùng nó để trả lời tình trạng hiện tại trong thực tế. Khi chạy live, API có thể rate limit, timeout hoặc thay đổi dữ liệu.

## 3. Bản đồ project

```text
agent.py                    # Học viên tự viết agent loop
pseudocode_agent.py         # Gợi ý cho agent loop
pseudocode_advanced.py      # Gợi ý kiểm tra nguồn
providers.py                # Adapter bốn provider, đã cung cấp
status_tools.py             # Tools + schema, đã cung cấp
run.py                      # CLI
fixtures/                   # Snapshot API, không sửa khi làm eval
evals/cases.json            # E1–E6: eval cơ bản
evals/advanced_cases.json   # A1–A8: eval nâng cao
evals/scenarios.py          # Timeout và prompt injection giả lập cho eval
evals/run_evals.py          # Chạy eval, chất lượng câu trả lời chấm thủ công
tests/                      # Tests offline
```

Một câu trả lời tốt phải phân biệt **trạng thái hiện tại theo thời điểm dữ liệu**, incident cũ, phạm vi ảnh hưởng và điều chưa biết. Status page không đủ để xác nhận nguyên nhân lỗi cụ thể của lớp.
