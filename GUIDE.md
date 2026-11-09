# Hướng dẫn lab

## Mục tiêu và thời gian

Toàn bộ các bước dưới đây thuộc bài lab. Giả định học viên đã biết Python, gọi LLM API và lý thuyết ReAct; giảng viên cung cấp sẵn tools, provider adapter và eval runner.

| Thời gian | Hoạt động | Kết quả |
|---|---|---|
| 0–15 phút | Khám phá tools và dữ liệu | Hiểu hai tools và giới hạn dữ liệu. |
| 15–70 phút | Bài 1: tự code agent loop | Model gọi tools và nhận lại kết quả. |
| 70–95 phút | Bài 2: xử lý lỗi và trace | Có giới hạn bước, trace và lỗi được xử lý. |
| 95–105 phút | Nghỉ | |
| 105–140 phút | Bài 3: chạy eval lần 1 | Có điểm, trace và danh sách lỗi. |
| 140–195 phút | Bài 4: phân tích và cải tiến | Chọn lỗi, giải thích nguyên nhân và implement cải tiến. |
| 195–225 phút | Bài 5: chạy eval lần 2 | So sánh điểm và lỗi với lần 1. |
| 225–240 phút | Demo và thảo luận | Trình bày kết quả, trace và giới hạn. |

Tổng: 240 phút, bao gồm 10 phút nghỉ. Eval gọi model thật cho cả agent và judge nên thời gian và chi phí có thể thay đổi. Mỗi case chạy độc lập; kết quả được ghi sau khi cả bộ hoàn tất.

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

Hoàn thiện `run_agent` trong `agent.py`. Các bước gợi ý có trong `agent.py`. Bạn không cần sửa provider adapter hay tool implementations.

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

## Bài 3 — Chạy eval lần 1

Sau khi hoàn thành agent loop, chạy bộ eval trên snapshot cố định:

```bash
python3 evals/run_evals.py --output eval_before.json
```

Bộ eval gồm **22 case E1–E6, A1–A8 và H1–H8**: điều tra nhiều provider, timeline, yêu cầu sai hoặc ngoài luồng, timeout, prompt injection, tìm kiếm giới hạn và nhiều bước tool call. H6 có thêm 40 mục nhiễu giả lập để kiểm tra agent khi thông tin dài. Các scenario giả lập chỉ áp dụng cho eval, không sửa snapshot gốc.

Mỗi case được chấm 0–100 bằng **LLM judge + kiểm tra bằng code**. Mở `eval_before.json`, xem `summary`, `grade.reason`, `grade.improvement`, `grade.mechanical`, answer và trace. Điểm judge là ước lượng, có thể sai hoặc bị ảnh hưởng bởi model; đối chiếu với `expected` và evidence. `completed` chỉ nói agent đã dừng bình thường.

Nếu một case bị lỗi hệ thống hoặc judge không trả JSON hợp lệ, case là `unscored` và điểm tổng là `null`. Sửa vấn đề cấu hình và chạy lại, không coi case đó là 0 hoặc bỏ qua để báo điểm tổng. `partial_mean_0_100` chỉ là trung bình các case đã chấm, không phải điểm toàn bộ.

## Bài 4 — Phân tích lỗi và cải tiến agent

Chọn một case điểm thấp hoặc một lỗi thấy trong trace. Ghi lại: case, câu trả lời, bằng chứng, nguyên nhân có thể xảy ra và thay đổi dự kiến. Đối chiếu những tình huống sau:

- **Nguồn và scope:** A2/A8. Địa chỉ URL có thật trong tool result không? Có tách phạm vi FedRAMP và các dịch vụ không?
- **Partial failure và prompt injection:** A3/A4/H5/H7. Tool timeout có bị nhầm là trạng thái dịch vụ không? Agent có làm theo chỉ dẫn giả trong tool result hoặc yêu cầu bịa dữ liệu không?
- **Nhiều bước và dữ liệu dài:** H1/H6. Agent có gọi tiếp khi thấy incident liên quan, bỏ qua dữ liệu nhiễu và nêu giới hạn khi output bị cắt không?
- **Yêu cầu sai hoặc ngoài luồng:** H2/H3/H4/H8. Agent có sửa tiền đề sai, từ chối bịa link hoặc sử dụng tool không cần thiết không?

Implement một thay đổi để giải quyết lỗi bạn đã chọn. Một ví dụ là kiểm tra URL nguồn trong `agent.py`: lưu URL từ `get_incident_details` thành công; nếu final answer không chứa URL incident đã quan sát, ghi event vào trace và yêu cầu model sửa trong `max_steps`. Không bắt URL nếu không có incident thành công. Đây chỉ là kiểm tra sự hiện diện một URL, không chứng minh tất cả claims đều có nguồn.

Chạy tests offline:

```bash
python3 -m unittest discover -s tests -v
```

Nếu chọn một cách cải tiến khác, vẫn cần hoàn thành contract kiểm tra nguồn trong `tests/test_validation.py`. Không sửa `fixtures/`, `evals/cases.json`, `evals/scenarios.py`, `evals/grading.py` hay rubric để làm case pass.

## Bài 5 — Chạy eval lần 2 và phân tích

Dùng cùng agent model, judge model, snapshot, max steps và dataset để chạy lại:

```bash
python3 evals/run_evals.py --output eval_after.json
```

So sánh điểm tổng, từng case và trace; nêu lỗi đã giải quyết, lỗi còn lại hoặc mới xuất hiện, số model calls, token và chi phí nếu provider cung cấp. Có thể chọn judge khác bằng `--judge-provider` và `--judge-model`, nhưng giữ nguyên giữa hai lần. Judge mặc định dùng cùng provider/model với agent: điểm có thể thiên lệch khi cùng model tự chấm.

Đây là **một vòng thực hành**: xây agent → chạy eval → phân tích lỗi → cải tiến → chạy lại. Chỉ một lần chạy mỗi phiên bản không chứng minh độ ổn định; không sửa expected để tối ưu điểm.

## Nộp bài

Nộp `agent.py`, `eval_before.json`, `eval_after.json` đã xóa thông tin nhạy cảm và ghi chú gồm: case được chọn, evidence trong trace, thay đổi, kết quả so sánh, giới hạn. Demo một trace nhiều bước và trình bày một lỗi agent.
