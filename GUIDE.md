# Hướng dẫn lab

## Mục tiêu và thời gian

Toàn bộ các bước dưới đây thuộc bài lab. Giả định học viên đã biết Python, gọi LLM API và lý thuyết ReAct; giảng viên cung cấp sẵn tools, provider adapter và eval runner.

| Thời gian | Hoạt động | Kết quả |
|---|---|---|
| 0–15 phút | Khám phá tools và dữ liệu | Hiểu hai tools và giới hạn dữ liệu. |
| 15–65 phút | Bài 1: tự code agent loop | Model gọi tools và nhận lại kết quả. |
| 65–95 phút | Bài 2: xử lý lỗi và trace | Có giới hạn bước, trace và lỗi được xử lý. |
| 95–105 phút | Nghỉ | |
| 105–155 phút | Bài 3: chạy eval | Chạy và phân tích E1–E6, A1–A8. |
| 155–220 phút | Bài 4: thực hành nâng cao | Kiểm tra nguồn, partial failure, dữ liệu thiếu và prompt injection. |
| 220–240 phút | Kiểm tra, demo và thảo luận | Trình bày kết quả, trace và giới hạn. |

Tổng: 240 phút, bao gồm 10 phút nghỉ. Hai bộ eval gọi model thật nên thời gian chạy có thể thay đổi; hãy bắt đầu từ đầu Bài 3 và làm các bước đọc trace trong lúc chờ.

## Khám phá tools

Chạy trực tiếp không cần LLM key:

```bash
python3 -c 'import json; from status_tools import StatusTools; print(json.dumps(StatusTools().get_status("github", "Actions"), ensure_ascii=False, indent=2))'
python3 -c 'import json; from status_tools import StatusTools; print(json.dumps(StatusTools().get_incident_details("cloudflare", "wp49bp8bqo6c"), ensure_ascii=False, indent=2))'
```

- `get_status(provider, component='')`: overall status, component khớp và tối đa 5 incident gần đây khớp chuỗi. Tool tìm trong 50 incident gần nhất; tìm không thấy **không** chứng minh incident không tồn tại.
- `get_incident_details(provider, incident_id)`: trả chi tiết một incident có trong 50 incident gần nhất. Tool giữ hai update mới nhất và update đầu tiên, mỗi update tối đa 900 ký tự. `truncated` và `updates_total` cho biết dữ liệu có thể đã bị lược bỏ.
- `execute(name, args)`: registry thực thi tool, trả dict. Lỗi dự kiến được chuyển thành `{ok: false, ...}` để model quan sát.

`component` là tìm chuỗi gần đúng, không phải semantic search: `cache purge` có thể khớp nhưng `xóa bộ nhớ đệm` có thể không. Đừng suy luận chắc chắn từ kết quả tìm kiếm rỗng. Status tổng quan không đồng nghĩa mọi component hay khu vực đều lỗi.

## Bài 1 — Tự viết agent loop

Hoàn thiện `run_agent` trong `agent.py`. Dùng `pseudocode_agent.py` khi cần. Bạn không cần sửa provider adapter hay tool implementations.

**Contract:**

```python
run_agent(question, provider, tools, max_steps=6) -> dict
```

- `provider.complete(messages, SCHEMAS)` trả `message`, `calls`, `finish`, `usage`.
- `message` là assistant message: append **nguyên vẹn** vào `messages` trước tool results.
- Mỗi call có `id`, `name`, `arguments` (JSON string). Parse arguments rồi gọi `tools.execute(name, args)`.
- Mỗi tool result gửi lại bằng `{'role': 'tool', 'tool_call_id': call_id, 'content': json_string}`. Xử lý **mọi** call trong response trước model call tiếp theo.
- Khi `finish == 'stop'` và không còn calls, trả answer; `length` hoặc lý do dừng khác không được coi là hoàn thành.
- Kết quả có tối thiểu `status` (`completed`, `max_steps`, `error`), `answer` (string), `trace` (list) và `usage` (list). Có thể thêm `error`.

`SCHEMAS` được import từ `status_tools`. Mỗi model call là một step, không phải mỗi tool call. Không yêu cầu model in chain-of-thought: trace chỉ cần step, finish, tool name, arguments và result. Đừng đưa key vào trace.

**Checkpoint:** Sau tool call đầu tiên, model có thực sự nhận được tool result gắn đúng ID không? Nếu có hai calls thì cả hai kết quả đã được trả chưa?

## Bài 2 — Kiểm soát lỗi

1. Giới hạn số lần gọi model bằng `max_steps`; hết lượt thì trả `max_steps`.
2. JSON arguments lỗi: trả tool result có `error: INVALID_ARGUMENTS` cho model, không crash.
3. Tool không tồn tại, provider không hợp lệ và timeout: đưa lỗi vào trace và cho model cơ hội báo không đủ dữ liệu.
4. Model bị cắt output (`finish == 'length'`) hoặc provider lỗi: trả `error`, không báo hoàn thành.
5. Chạy `python3 -m unittest discover -s tests -v`; xem từng test để hiểu contract.

Lỗi provider có thể kết thúc run; lỗi tool nên được trả làm observation. Test offline không chứng minh agent trả lời đúng ngoài thực tế.

## Bài 3 — Chạy eval

Chạy hai bộ eval sau khi hoàn thành agent loop. Mỗi case là một run độc lập trên snapshot cố định:

```bash
python3 evals/run_evals.py --output eval_results_basic.json
python3 evals/run_evals.py --suite advanced --output eval_results_advanced.json
```

Bộ cơ bản gồm **E1–E6**; bộ nâng cao gồm **A1–A8**. File kết quả chứa câu hỏi, kỳ vọng, status, answer, trace và usage. `completed` chỉ nói loop kết thúc bình thường: bạn phải đối chiếu câu trả lời với evidence và tự chấm theo [RUBRIC.md](RUBRIC.md).

| Case | Tình huống cần phân tích |
|---|---|
| E1–E6 | Status hiện tại và lịch sử, scope FedRAMP, khu vực, incident nhiều component, dữ liệu thiếu và timeout. |
| A1 | Điều tra GitHub và Cloudflare, dẫn nguồn cho cả hai; không suy đoán cùng nguyên nhân. |
| A2 | Tìm phạm vi FedRAMP trong update cũ, không kết luận quá mức. |
| A3 | Cloudflare timeout giả lập, GitHub vẫn hoạt động: báo kết quả từng phần. |
| A4 | Tool result có prompt injection giả lập: bỏ qua chỉ dẫn giả, trả lời đúng và dẫn nguồn. |
| A5 | Không suy ra danh sách đầy đủ khi tool chỉ tìm trong 50 incident gần nhất. |
| A6 | Theo tham chiếu từ incident này sang incident khác, phân biệt thông tin xác nhận và chưa xác nhận. |
| A7 | Không quy lỗi tại Việt Nam cho incident Phoenix khi chưa đủ bằng chứng. |
| A8 | So sánh hai incident khác provider, dẫn cả hai nguồn, không bịa nguyên nhân chung. |

`evals/scenarios.py` tạo timeout và chèn chỉ dẫn giả **chỉ khi chạy eval**; snapshot gốc không bị thay đổi. Chỉ dẫn trong tool result là dữ liệu không đáng tin, không phải yêu cầu cho agent. E6 cũng giả lập timeout. Ghi lại provider, model, cấu hình, số lần chạy, điểm, token và các trường hợp agent trả lời chưa đúng hoặc chưa đủ.

## Bài 4 — Thực hành nâng cao

### 4.1. Kiểm tra bằng chứng và nguồn

Dùng kết quả A1, A4 và A8 để kiểm tra URL trong tool results và final answer. Implement một bước validation trong `agent.py`:

1. Khi `get_incident_details` thành công, lưu URL incident mà tool trả về.
2. Khi model đưa final answer, nếu đã có URL incident nhưng câu trả lời không chứa **bất kỳ URL incident nào đã quan sát**, ghi validation event vào trace và yêu cầu model sửa.
3. Lần gọi sửa phải tính vào `max_steps`. Nếu hết lượt, không trả `completed`. Không yêu cầu URL incident khi tool thất bại hoặc không tìm được incident.
4. Chạy tests offline, xem `pseudocode_advanced.py` nếu cần.

Đây là một **kiểm tra tối thiểu**: URL xuất hiện không chứng minh nó hỗ trợ mọi claim, và chưa bảo đảm có đủ nguồn cho cả hai provider. Với A1 và A8, vẫn phải tự kiểm tra từng nguồn.

### 4.2. Partial failure và prompt injection

- Đọc trace A3: GitHub trả gì, Cloudflare lỗi gì, model có báo rõ phần chưa kiểm tra được không? Đếm số lần gọi lại. Đọc E6 để so sánh khi tool được hỏi đều timeout; không đồng nhất timeout với trạng thái dịch vụ.
- Đọc trace A4: xác định chỉ dẫn giả trong tool result và kiểm tra final answer không làm theo nó. Đối chiếu nội dung và URL thật trong tool output. Một lần vượt qua không chứng minh agent an toàn trước mọi kiểu injection.

Ghi một hạn chế hoặc lỗi quan sát được của mỗi case vào ghi chú; không hard-code câu trả lời theo case.

### 4.3. Search, context và dữ liệu chưa đầy đủ

Phân tích A5 và A6: tool chỉ tìm trong 50 incident gần nhất; detail giữ hai update mới nhất cùng update đầu tiên. Một update có thể bị cắt (`truncated`) hoặc bị bỏ qua giữa timeline (`updates_total`). Ghi agent có làm rõ giới hạn dữ liệu không và việc đọc incident liên quan có bổ sung evidence gì. Với A2 và A7, đối chiếu phạm vi khách hàng, địa lý và uncertainty.

## Kiểm tra và nộp bài

Sau khi hoàn thành bước kiểm tra nguồn, chạy tests và eval để kiểm tra agent:

```bash
python3 -m unittest discover -s tests -v
python3 evals/run_evals.py --output eval_results_basic.json
python3 evals/run_evals.py --suite advanced --output eval_results_advanced.json
```

Đọc câu trả lời và trace, tự chấm theo rubric. Các model có thể trả lời khác nhau giữa những lần chạy; một lần pass chưa chứng minh độ ổn định. Không sửa `fixtures/`, các bộ case, `evals/scenarios.py` hay rubric để làm case pass.

Nộp `agent.py`, kết quả hai bộ eval đã xóa thông tin nhạy cảm và ghi chú về một trường hợp agent trả lời chưa đúng hoặc chưa đủ. Demo agent và một trace nâng cao; cho biết đang dùng snapshot hay live và thời điểm dữ liệu.
