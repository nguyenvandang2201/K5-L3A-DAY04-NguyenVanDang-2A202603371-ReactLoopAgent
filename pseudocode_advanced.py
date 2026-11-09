# ADVANCED: Evidence gate (không chạy file này)
# Khi tool result là incident detail thành công, ghi nhớ URL được trả về.
# Khi model đề xuất final answer, nếu đã có URL incident nhưng answer thiếu tất cả URL đã thấy:
#   Ghi event validation_missing_source vào trace.
#   Gửi lại yêu cầu bổ sung URL đã có trong tool result; không tự bịa URL.
#   Lặp tiếp trong budget max_steps; nếu hết budget, không trả completed.
# Nếu có URL đã thấy trong answer, cho phép kết thúc nhưng vẫn phải tự chấm tính đúng đắn.
# Nâng cao hơn: yêu cầu đủ nguồn cho các claims / từng provider; xử lý partial failure.
# CHÚ Ý: checks bằng code chỉ kiểm tra điều kiện hữu hạn, không chứng minh factuality.
