# -*- coding: utf-8 -*-  # Cho phép ghi chú tiếng Việt trong tệp mô hình.
import os  # Kiểm tra xem mô hình đã được lưu chưa.
import numpy as np  # Tạo và xử lý ma trận dữ liệu số.
import joblib  # Lưu mô hình vào đĩa và tải lại ở lần chạy sau.
from sklearn.ensemble import RandomForestRegressor  # Nhập mô hình hồi quy Random Forest.
from sklearn.model_selection import train_test_split  # Chia dữ liệu thành tập huấn luyện và kiểm tra.
from sklearn.metrics import mean_absolute_error  # Tính sai số tuyệt đối trung bình MAE.

TEP_MO_HINH = "traffic_time_model.joblib"  # Đặt tên tệp chứa mô hình đã huấn luyện.

def ma_hoa_phuong_tien(phuong_tien):  # Chuyển tên phương tiện thành số để đưa vào mô hình.
    """Mỗi phương tiện được gán một mã số cố định."""  # Mô tả quy tắc mã hóa.
    bang_ma = {"Xe máy": 0, "Ô tô cá nhân": 1, "Taxi": 2, "Xe buýt": 3, "Máy bay": 4, "Xe điện": 5}  # Định nghĩa bảng mã phương tiện.
    return bang_ma.get(phuong_tien, 0)  # Trả về mã tương ứng, mặc định là xe máy nếu không khớp.

def huan_luyen_mo_hinh(huan_luyen_lai=False):  # Huấn luyện mô hình hoặc tải mô hình đã lưu.
    """Mô hình mẫu dùng dữ liệu tổng hợp để minh họa; không đại diện dữ liệu giao thông thật."""  # Nêu rõ giới hạn dữ liệu huấn luyện.
    if os.path.exists(TEP_MO_HINH) and not huan_luyen_lai:  # Kiểm tra có thể tái sử dụng mô hình cũ không.
        return joblib.load(TEP_MO_HINH), None  # Tải mô hình đã lưu và không tính lại MAE.
    rng = np.random.default_rng(42)  # Cố định bộ sinh số ngẫu nhiên để kết quả tái lập được.
    so_mau = 1600  # Chọn số dòng dữ liệu tổng hợp.
    quang_duong = rng.uniform(1, 120, so_mau)  # Sinh quãng đường giả lập từ 1 đến 120 km.
    toc_do = rng.uniform(15, 70, so_mau)  # Sinh tốc độ trung bình giả lập.
    thoi_gian_goc = quang_duong / toc_do * 60  # Tính thời gian cơ bản theo công thức quãng đường chia tốc độ.
    he_so_giao_thong = rng.uniform(1.0, 1.8, so_mau)  # Sinh hệ số ùn tắc giả lập.
    ma_phuong_tien = rng.integers(0, 6, so_mau)  # Sinh mã phương tiện cho từng mẫu.
    he_so_phuong_tien = np.choose(ma_phuong_tien, [1.0, 1.05, 1.08, 1.35, 0.35, 1.0])  # Mô phỏng ảnh hưởng của từng loại phương tiện.
    nhieu = rng.normal(0, 3, so_mau)  # Thêm nhiễu ngẫu nhiên để dữ liệu không hoàn toàn lý tưởng.
    nhan_thoi_gian = np.maximum(1, thoi_gian_goc * he_so_giao_thong * he_so_phuong_tien + nhieu)  # Tạo nhãn thời gian cần dự đoán.
    dac_trung = np.column_stack([quang_duong, thoi_gian_goc, he_so_giao_thong, ma_phuong_tien])  # Ghép các biến đầu vào thành ma trận.
    x_train, x_test, y_train, y_test = train_test_split(dac_trung, nhan_thoi_gian, test_size=0.2, random_state=42)  # Chia 80% huấn luyện và 20% kiểm tra.
    mo_hinh = RandomForestRegressor(n_estimators=120, max_depth=14, random_state=42, n_jobs=-1)  # Khởi tạo mô hình Random Forest.
    mo_hinh.fit(x_train, y_train)  # Huấn luyện mô hình trên tập huấn luyện.
    du_doan_test = mo_hinh.predict(x_test)  # Dự đoán thời gian cho tập kiểm tra.
    mae = mean_absolute_error(y_test, du_doan_test)  # Tính MAE trên dữ liệu tổng hợp.
    joblib.dump(mo_hinh, TEP_MO_HINH)  # Lưu mô hình để tái sử dụng.
    return mo_hinh, mae  # Trả về mô hình và chỉ số MAE.

def du_doan_thoi_gian(km, phut_co_ban, he_so_giao_thong, phuong_tien):  # Dự đoán thời gian di chuyển bằng mô hình.
    """Trả về (thời gian phút, ghi chú về nguồn mô hình)."""  # Mô tả kết quả trả về.
    try:  # Bắt lỗi thư viện hoặc lỗi tải mô hình.
        mo_hinh, mae = huan_luyen_mo_hinh()  # Lấy mô hình đã huấn luyện hoặc huấn luyện mới.
        dau_vao = np.array([[km, phut_co_ban, he_so_giao_thong, ma_hoa_phuong_tien(phuong_tien)]])  # Chuẩn bị một mẫu theo đúng thứ tự đặc trưng.
        thoi_gian = float(mo_hinh.predict(dau_vao)[0])  # Dự đoán thời gian từ mô hình.
        if mae is None:  # Xử lý khi mô hình được tải từ tệp đã có.
            ghi_chu = "Random Forest dùng dữ liệu tổng hợp minh họa; MAE chưa được tính lại trong lần chạy này."  # Nêu nguồn mô hình.
        else:  # Xử lý khi mô hình vừa được huấn luyện.
            ghi_chu = f"Random Forest; MAE kiểm tra trên dữ liệu tổng hợp ≈ {mae:.2f} phút, không đại diện độ chính xác thực tế."  # Nêu kết quả đánh giá và giới hạn.
        return max(1.0, thoi_gian), ghi_chu  # Trả về thời gian hợp lệ và ghi chú.
    except Exception:  # Dự phòng nếu mô hình không thể chạy.
        return max(1.0, phut_co_ban * he_so_giao_thong), "Mô hình chưa chạy được; dùng công thức dự phòng."  # Trả về thời gian theo công thức đơn giản.
