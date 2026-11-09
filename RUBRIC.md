# Rubric

Tổng **100 điểm**. Test pass là bằng chứng kỹ thuật, không thay thế việc đọc trace và câu trả lời.

| Nội dung | Điểm | Tiêu chí |
|---|---:|---|
| Agent loop | 35 | Gọi model và tool thật qua interface; append assistant message + đúng tool-call IDs; xử lý nhiều calls; dừng đúng. |
| Robustness và trace | 20 | `max_steps`, invalid JSON, tool error, model dừng bất thường; trace đủ để debug. |
| Eval và kết luận | 25 | Chạy E1–E6 và A1–A8; phân tích scope, partial failure, injection, nhiều nguồn và giới hạn dữ liệu; không bịa nguyên nhân. |
| Kiểm tra nguồn và trình bày | 20 | Implement validation nguồn, xử lý giới hạn bước; trình bày một trace và giới hạn trong kết quả. |

Gợi ý chấm từng case: **0** = sai hoặc bịa thông tin; **1** = không khẳng định sai nhưng thiếu bằng chứng/ý quan trọng; **2** = đúng, đủ trong phạm vi snapshot, có nguồn và giới hạn. E6 đạt 2 khi báo không lấy được dữ liệu và không khẳng định status. Nếu tool không cung cấp đủ dữ liệu, câu trả lời nói rõ chưa đủ vẫn đúng về calibration nhưng có thể chưa đầy đủ cho yêu cầu.

Giảng viên xem `expected` ở `evals/cases.json`; đó là hướng dẫn chấm thủ công, không phải ground truth toàn diện. Test một lần không chứng minh độ ổn định của model. Nêu rõ case đã chạy, provider/model và số lần khi báo cáo kết quả.

