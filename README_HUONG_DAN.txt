TRAFFICMIND AI - PHIÊN BẢN GIAO DIỆN WEB FLASK + HTML/CSS/JAVASCRIPT
===================================================================

1. CẤU TRÚC DỰ ÁN
- app.py: máy chủ Flask, API và lưu lịch sử CSV.
- data.py: tìm địa chỉ, lấy tuyến đường từ OSRM/OpenStreetMap, công thức khoảng cách dự phòng.
- model.py: mô hình Random Forest dự đoán thời gian (dữ liệu tổng hợp minh họa).
- formula.py: công thức ước tính chi phí và hệ số giao thông.
- templates/index.html: cấu trúc giao diện HTML.
- static/css/style.css: thiết kế giao diện và responsive.
- static/js/app.js: tương tác trang, bản đồ, so sánh phương tiện và lịch sử.
- history/: nơi lưu lịch sử chuyến đi.

2. CÁCH CHẠY TRÊN WINDOWS POWERSHELL
Mở PowerShell tại thư mục dự án, sau đó chạy lần lượt:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py

Mở trình duyệt và truy cập: http://127.0.0.1:5000
Để dừng máy chủ, quay lại PowerShell và nhấn Ctrl+C.

Nếu PowerShell báo chặn việc kích hoạt môi trường, chỉ cho phiên PowerShell hiện tại có thể dùng:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
Sau đó thử kích hoạt lại môi trường.

3. LƯU Ý VỀ DỮ LIỆU VÀ GIỚI HẠN
- Cần kết nối Internet để tra địa chỉ, bản đồ và tuyến đường. Các dịch vụ công cộng có giới hạn sử dụng; không gửi yêu cầu quá dày.
- Bản đồ hiển thị bằng Leaflet và OpenStreetMap. Tuyến đường bộ được lấy từ dịch vụ OSRM công cộng khi có thể.
- Dự đoán ùn tắc dùng hệ số theo khung giờ và mô hình minh họa, không phải dữ liệu giao thông trực tiếp.
- Random Forest được huấn luyện trên dữ liệu tổng hợp để minh họa quy trình học máy; kết quả không đại diện độ chính xác thực tế.
- Giá xe máy, ô tô, taxi, xe buýt, máy bay và xe điện là ước tính minh họa. Không phải báo giá của nhà cung cấp.
- So sánh phương tiện dùng cùng quãng đường làm cơ sở so sánh chi phí; không khẳng định tất cả phương tiện có thể đi cùng tuyến. Máy bay cần dữ liệu sân bay/chuyến bay, xe buýt cần dữ liệu tuyến và lịch chạy thực tế.
- Nếu Windows Application Control chặn thư viện nhị phân NumPy hoặc scikit-learn, đây là vấn đề chính sách bảo mật Windows, không phải lỗi HTML. Không nên tắt chính sách bảo mật; cần xem nhật ký CodeIntegrity hoặc hỏi quản trị viên máy.

4. MÔ PHỎNG KẸT XE (TÍNH NĂNG BỔ SUNG)
- Trong màn hình Tìm đường thông minh, kéo xuống phần “Mô phỏng kẹt xe”.
- Cách 1: bấm “Đặt điểm trên bản đồ”, rồi bấm đúng vị trí muốn tạo tình huống kẹt xe.
- Cách 2: nhập địa chỉ (nên thêm phường/quận và TP.HCM), bấm “Tìm”. Ứng dụng sẽ chọn kết quả địa lý đầu tiên và đưa bản đồ đến đó.
- Chọn mức độ Nhẹ/Vừa/Nặng và bán kính 300 m/500 m/1 km/2 km trước khi tạo điểm. Mức phạt minh họa lần lượt khoảng +5/+12/+22 phút nếu tuyến đi qua vùng ảnh hưởng.
- Điểm kẹt xe có thể bật/tắt hoặc xóa riêng; “Xóa tất cả” đặt lại kịch bản. Điểm được lưu trong data/simulated_jams.json.
- Sau khi thêm/bật/tắt/xóa điểm, nếu đã có chuyến đi thì ứng dụng tự tính lại. Máy chủ so sánh tối đa ba phương án OSRM trả về (nếu có), cộng thời gian phạt giả lập cho tuyến gần vùng kẹt xe rồi chọn phương án có thời gian ước tính thấp nhất. Dịch vụ OSRM công cộng có thể chỉ trả một phương án.
- Khi tuyến được chọn bị ảnh hưởng, ứng dụng hiển thị cảnh báo và thử phát tiếng bíp ngắn. Trình duyệt có thể chặn âm thanh; hãy bấm nút tìm đường nếu không nghe thấy.
- Tất cả vòng tròn và thời gian cộng thêm đều là KỊCH BẢN GIẢ LẬP do người dùng đặt. Đây không phải dữ liệu ùn tắc thực tế và không chứng minh mô hình dự đoán chính xác ngoài đời.

5. SƠ ĐỒ TÍNH NĂNG MÔ PHỎNG
- docs/so_do/08_dat_diem_mo_phong.svg: chọn điểm trên bản đồ hoặc theo địa chỉ.
- docs/so_do/09_cham_diem_tuyen.svg: tính tác động của vùng mô phỏng và chọn phương án thời gian ước tính thấp nhất.
- docs/so_do/10_canh_bao_reset.svg: cảnh báo, bật/tắt, xóa điểm và tính lại chuyến đi.
- docs/THUYET_MINH_MO_PHONG_KET_XE.txt: giải thích API, các hàm, công thức và các bước kiểm thử.

6. GIỚI HẠN KHOA HỌC
- Dữ liệu mô phỏng là dữ liệu kịch bản thủ công, không phải cảm biến giao thông. Phần học máy Random Forest hiện dùng dữ liệu tổng hợp để minh họa quy trình học máy.
- Tác động mô phỏng được cộng bằng quy tắc thời gian phạt theo mức độ và khoảng cách tới tuyến; đây là mô hình minh họa có thể giải thích, không phải dự báo tốc độ đường thực tế.
- OSRM dùng thời gian định tuyến ước tính, không cung cấp dữ liệu giao thông trực tiếp. Muốn hiển thị tình hình thực tế cần tích hợp nhà cung cấp có hỗ trợ traffic và khóa API hợp lệ.

7. ĐỒ ÁN
Đề tài: Ứng dụng tính lộ trình, ước tính chi phí và dự đoán thời gian di chuyển bằng học máy.
Giao diện được tách riêng để có thể chỉnh sửa HTML/CSS/JavaScript mà không trộn với phần xử lý Python.


8. BỔ SUNG GỢI Ý TUYẾN VÒNG TRÁNH KẸT XE
- Khi có điểm kẹt xe mô phỏng đang bật, máy chủ thử tạo thêm các tuyến đường vòng bằng cách gửi các điểm trung gian nằm ngoài bán kính vùng kẹt xe tới OSRM.
- Kết quả tuyến được chấm điểm theo thời gian định tuyến cộng thời gian phạt mô phỏng. Giao diện liệt kê các tuyến và cho phép bấm vào từng phương án để xem tuyến đó trên bản đồ.
- Tuyến vòng tránh chỉ được tạo khi OSRM tìm được đường qua điểm trung gian đó; không đảm bảo luôn có nhiều tuyến ở mọi địa chỉ. Nếu không có tuyến thay thế khả thi, ứng dụng phải thông báo rõ thay vì bịa đường.


9. BỔ SUNG THUẬT TOÁN A*
- Dự án chạy A* trên đồ thị ghép từ các hình học tuyến ứng viên mà OSRM trả về và các tuyến vòng tránh đã tạo.
- Chi phí cạnh được ước tính theo thời gian đoạn đường và cộng phạt nếu trung điểm cạnh nằm trong vùng kẹt xe mô phỏng.
- A* chọn đường có tổng chi phí thấp trong đồ thị ứng viên, sau đó ứng dụng so sánh với các phương án còn lại.
- GIỚI HẠN QUAN TRỌNG: đây chưa phải A* trên toàn bộ mạng đường OpenStreetMap. Khả năng tìm đường mới bị giới hạn bởi các tuyến ứng viên đã lấy được từ OSRM. Không được mô tả là A* điều hướng toàn thành phố hoặc dữ liệu giao thông thời gian thực.
- Random Forest là phần học máy; A* là thuật toán tìm kiếm đường đi, không phải mô hình học máy.

10. PHÒNG THÍ NGHIỆM HỌC MÁY THEO CHƯƠNG 1-9
- Mở menu “Phòng thí nghiệm ML” ở thanh bên trái, bấm “Chạy thực nghiệm các mô hình”.
- Chương 1: Linear Regression dự đoán thời gian (hồi quy).
- Chương 2: Logistic Regression phân loại mức ùn tắc.
- Chương 3: Gaussian Naive Bayes phân loại mức ùn tắc.
- Chương 4: K-Nearest Neighbors (KNN) phân loại mức ùn tắc.
- Chương 5: Decision Tree, Random Forest (hồi quy và phân loại).
- Chương 6: Support Vector Machine (SVM) phân loại mức ùn tắc.
- Chương 7: đánh giá bằng MAE, RMSE, R² cho hồi quy; Accuracy, Precision, Recall, F1 và Confusion Matrix cho phân loại.
- Chương 8: K-Means phân cụm ba nhóm đặc trưng giao thông; Silhouette dùng tham khảo chất lượng cụm.
- Chương 9: MLPRegressor dự đoán thời gian; StandardScaler được đặt trong pipeline để chuẩn hóa đặc trưng.
- Tệp ml_lab.py chứa bộ dữ liệu tổng hợp, huấn luyện, đánh giá và kết quả K-Means. app.py cung cấp API /api/ml-lab; app.js gọi API và trình bày bảng kết quả.

CẢNH BÁO HỌC THUẬT:
- Phòng thí nghiệm tạo 2.400 mẫu dữ liệu tổng hợp có quy tắc mô phỏng. Kết quả chỉ chứng minh quy trình code có thể chạy và minh họa cách so sánh thuật toán; KHÔNG chứng minh dự đoán chính xác giao thông thật.
- Trong phần phân loại, biến mức ùn tắc được dùng để sinh nhãn không được đưa ngược vào đặc trưng đầu vào, nhằm tránh rò rỉ nhãn.
- Muốn báo cáo kết quả thực tế, cần thay dữ liệu tổng hợp bằng dữ liệu giao thông có nguồn, giấy phép và thời gian thu thập rõ ràng; sau đó huấn luyện/đánh giá lại.
- Các chương 2-6 dùng bài toán phân loại ba mức (nhẹ/vừa/cao) được tạo theo quy tắc mô phỏng. Chương 8 là học không giám sát. Chương 7 là đánh giá, không phải mô hình.
- Không sử dụng Deep Learning ngoài Chương 9; MLPRegressor là mô hình mạng nơ-ron nhiều lớp ở mức phù hợp với nội dung MLP đã học.
