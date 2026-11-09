# BÀI 1: Agent loop (chỉ pseudocode, không import hoặc chạy file này)
# Tạo messages gồm SYSTEM_PROMPT và câu hỏi user.
# Tạo trace rỗng; usage rỗng hoặc danh sách.
# Lặp tối đa max_steps lần gọi model:
#   Gọi provider.complete(messages, SCHEMAS).
#   Lưu response["message"] vào messages trước khi xử lý tool calls.
#   Ghi usage và số bước vào trace.
#   Nếu response có calls:
#       Với từng call, parse JSON arguments thành dict.
#       Nếu JSON lỗi, tạo tool result báo lỗi, không crash.
#       Nếu hợp lệ, gọi tools.execute(name, args).
#       Ghi tên, arguments, kết quả vào trace.
#       Append role=tool, tool_call_id=call id, content=JSON string vào messages.
#       Tiếp tục lặp sau khi đã trả kết quả cho TẤT CẢ calls.
#   Nếu finish là stop và không có calls: return completed + answer + trace + usage.
#   Nếu model dừng vì lý do khác: return error; đừng coi output bị cắt là hoàn chỉnh.
# Hết vòng lặp: return max_steps, không nói agent đã hoàn tất.
# BÀI 2: Xem GUIDE.md, bổ sung error handling và quan sát trace.
