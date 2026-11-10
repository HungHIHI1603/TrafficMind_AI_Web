# -*- coding: utf-8 -*-  # Cho phép chú thích và chuỗi tiếng Việt.
# Tệp này chỉ chứa công thức và tham số tính toán để tách biệt khỏi giao diện và mô hình học máy.

BANG_GIA = {  # Khai báo hệ số giá tham khảo theo từng phương tiện.
    "Xe máy": {"phi_co_ban": 0, "gia_moi_km": 1200, "gia_moi_nguoi": 0},  # Chi phí nhiên liệu và hao mòn xe máy giả định.
    "Ô tô cá nhân": {"phi_co_ban": 0, "gia_moi_km": 4500, "gia_moi_nguoi": 0},  # Chi phí nhiên liệu và vận hành ô tô giả định.
    "Taxi": {"phi_co_ban": 12000, "gia_moi_km": 14000, "gia_moi_nguoi": 0},  # Phí cơ bản và giá/km taxi minh họa, không đại diện hãng cụ thể.
    "Xe buýt": {"phi_co_ban": 10000, "gia_moi_km": 0, "gia_moi_nguoi": 10000},  # Giá vé tham khảo cho từng hành khách.
    "Máy bay": {"phi_co_ban": 900000, "gia_moi_km": 1800, "gia_moi_nguoi": 0},  # Công thức minh họa, không phải giá vé thực tế.
    "Xe điện": {"phi_co_ban": 0, "gia_moi_km": 700, "gia_moi_nguoi": 0},  # Điện năng và hao mòn xe điện giả định.
}  # Kết thúc bảng tham số giá.

def tinh_chi_phi(quang_duong_km, phuong_tien, so_nguoi=1):  # Tính tổng chi phí dự toán cho một chuyến đi.
    """Công thức tổng = phí cơ bản + quãng đường × giá/km + số người × giá/người."""  # Mô tả công thức tính phí.
    tham_so = BANG_GIA[phuong_tien]  # Lấy các hệ số của phương tiện được chọn.
    phi_co_ban = tham_so["phi_co_ban"]  # Đọc phí cơ bản.
    phi_quang_duong = max(0, quang_duong_km) * tham_so["gia_moi_km"]  # Tính chi phí biến đổi theo quãng đường.
    phi_hanh_khach = max(1, so_nguoi) * tham_so["gia_moi_nguoi"]  # Tính chi phí phụ thuộc số người.
    return phi_co_ban + phi_quang_duong + phi_hanh_khach  # Trả về tổng chi phí dự toán bằng VNĐ.

def uoc_tinh_giao_thong(khung_gio):  # Ước tính nhãn giao thông dựa trên khung giờ.
    """Đây là quy tắc minh họa, không phải dữ liệu kẹt xe thời gian thực."""  # Cảnh báo về bản chất ước lượng.
    bang_giao_thong = {  # Khai báo hệ số thời gian minh họa cho từng khung giờ.
        "Ngay bây giờ": {"he_so": 1.20, "nhan": "Có thể đông"},  # Mức mặc định minh họa.
        "Giờ cao điểm sáng": {"he_so": 1.55, "nhan": "Nguy cơ kẹt xe cao"},  # Mô phỏng giờ cao điểm buổi sáng.
        "Giờ cao điểm chiều": {"he_so": 1.65, "nhan": "Nguy cơ kẹt xe cao"},  # Mô phỏng giờ cao điểm buổi chiều.
        "Ngoài giờ cao điểm": {"he_so": 1.08, "nhan": "Dự kiến thông thoáng hơn"},  # Mô phỏng thời gian ít đông xe hơn.
    }  # Kết thúc bảng hệ số giao thông.
    return bang_giao_thong.get(khung_gio, bang_giao_thong["Ngay bây giờ"])  # Trả về thông tin giao thông phù hợp.

def tinh_thoi_gian_co_ket_xe(thoi_gian_co_ban_phut, he_so_giao_thong):  # Tính thời gian khi áp dụng hệ số ùn tắc.
    """Công thức: thời gian điều chỉnh = thời gian cơ bản × hệ số giao thông."""  # Mô tả công thức thời gian.
    return max(1.0, thoi_gian_co_ban_phut * he_so_giao_thong)  # Trả về số phút dự toán, tối thiểu một phút.
