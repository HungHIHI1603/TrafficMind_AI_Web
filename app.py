# -*- coding: utf-8 -*-  # Cho phép ghi chú và chuỗi tiếng Việt trong tệp nguồn.
from flask import Flask, render_template, request, jsonify  # Nhập Flask để tạo máy chủ web và xử lý yêu cầu từ giao diện.
from datetime import datetime  # Lấy thời gian hiện tại để lưu lịch sử chuyến đi.
import csv  # Ghi lịch sử chuyến đi ra tệp CSV mà không cần Pandas.
import os  # Kiểm tra thư mục và tệp lịch sử.
import json  # Đọc và ghi các điểm kẹt xe mô phỏng dưới dạng JSON.
import math  # Tính khoảng cách từ điểm kẹt xe đến các điểm trên tuyến đường.
import uuid  # Tạo mã riêng cho từng tình huống kẹt xe.
import heapq  # Dùng hàng đợi ưu tiên để triển khai thuật toán tìm đường A*.
from data import tim_dia_diem, tim_goi_y_dia_diem, lay_lo_trinh, lay_cac_lo_trinh, tao_tuyen_ne_tranh_diem, khoang_cach_du_phong  # Nhập hàm tìm tọa độ và định tuyến.
from model import du_doan_thoi_gian  # Nhập mô hình học máy dự đoán thời gian.
from formula import tinh_chi_phi, uoc_tinh_giao_thong, tinh_thoi_gian_co_ket_xe, BANG_GIA  # Nhập công thức tính phí và giao thông.
from ml_lab import chay_thuc_nghiem  # Nhập phòng thí nghiệm so sánh mô hình Chương 1-9.

app = Flask(__name__)  # Khởi tạo ứng dụng web Flask.
TEP_LICH_SU = os.path.join('history', 'lich_su_lo_trinh.csv')  # Xác định nơi lưu lịch sử chuyến đi.
TEP_KET_XE_MO_PHONG = os.path.join('data', 'simulated_jams.json')  # Tệp lưu các điểm kẹt xe mô phỏng để không mất khi tải lại trang.
PHUONG_TIEN = ['Xe máy', 'Ô tô cá nhân', 'Taxi', 'Xe buýt', 'Máy bay', 'Xe điện']  # Khai báo các phương tiện trong giao diện.

@app.route('/')  # Khai báo đường dẫn trang chủ.
def trang_chu():  # Hàm hiển thị giao diện chính.
    return render_template('index.html', phuong_tien=PHUONG_TIEN)  # Gửi trang HTML cùng danh sách phương tiện cho trình duyệt.

@app.route('/api/geocode')  # Tạo API gợi ý địa chỉ khi người dùng đang nhập.
def api_goi_y_dia_chi():  # Tìm các địa chỉ gần khớp để giao diện hiển thị danh sách gợi ý.
    truy_van = str(request.args.get('q', '')).strip()  # Đọc từ khóa tìm kiếm từ URL.
    if len(truy_van) < 3:  # Chỉ tìm khi có ít nhất ba ký tự.
        return jsonify({'results': []})  # Trả danh sách rỗng khi từ khóa quá ngắn.
    goi_y = tim_goi_y_dia_diem(truy_van, gioi_han=5)  # Gọi dịch vụ địa lý để tìm tối đa năm gợi ý.
    return jsonify({'results': goi_y})  # Trả gợi ý và tọa độ về trình duyệt.


def khoa_nut(toa_do):
    """Chuẩn hóa tọa độ thành mã nút để gộp các điểm giao nhau gần nhau."""
    return (round(float(toa_do[0]), 5), round(float(toa_do[1]), 5))


def tinh_chi_phi_doan_a_star(diem_a, diem_b, phut_co_ban, khoang_cach_tuyen_km, he_so_gio, cac_diem_ket_xe):
    """Tính chi phí phút của một cạnh; phần cộng thêm do kẹt xe là dữ liệu mô phỏng."""
    do_dai_km = khoang_cach_hai_diem_km(diem_a, diem_b)
    if khoang_cach_tuyen_km <= 0:
        return max(0.01, phut_co_ban)
    chi_phi = (do_dai_km / khoang_cach_tuyen_km) * phut_co_ban * he_so_gio
    # Ước lượng mức phạt trên cạnh nếu cạnh nằm trong vùng kẹt xe mô phỏng.
    diem_giua = ((diem_a[0] + diem_b[0]) / 2, (diem_a[1] + diem_b[1]) / 2)
    for jam in cac_diem_ket_xe:
        if not jam.get('dang_bat', True):
            continue
        tam = (float(jam['vi_do']), float(jam['kinh_do']))
        ban_kinh_km = float(jam.get('ban_kinh_m', 500)) / 1000
        if khoang_cach_hai_diem_km(diem_giua, tam) <= ban_kinh_km:
            phat = {'nhe': 5, 'vua': 12, 'nang': 22}.get(jam.get('muc_do', 'vua'), 12)
            chi_phi += phat * min(1.0, max(0.1, do_dai_km / max(ban_kinh_km, 0.1)))
    return max(0.001, chi_phi)


def tim_tuyen_bang_a_star(cac_tuyen, cac_diem_ket_xe, he_so_gio=1.0):
    """Chạy A* trên đồ thị được tạo từ các tuyến đường OSRM ứng viên.
    A* chỉ tìm trong mạng các tuyến ứng viên đã nhận được, không tự tải toàn bộ mạng đường OSM.
    """
    do_thi = {}
    thong_tin_canh = {}
    toa_do_nut = {}
    for so_tuyen, tuyen in enumerate(cac_tuyen):
        toa_do = tuyen.get('toa_do') or []
        if len(toa_do) < 2:
            continue
        tong_km = max(float(tuyen.get('km', 0)), 0.001)
        phut_goc = max(float(tuyen.get('phut', 0)), 0.01)
        for diem in toa_do:
            k = khoa_nut(diem)
            toa_do_nut[k] = k
            do_thi.setdefault(k, [])
        for i in range(len(toa_do) - 1):
            a, b = khoa_nut(toa_do[i]), khoa_nut(toa_do[i + 1])
            if a == b:
                continue
            phut_canh = tinh_chi_phi_doan_a_star(toa_do[i], toa_do[i+1], phut_goc, tong_km, he_so_gio, cac_diem_ket_xe)
            km_canh = khoang_cach_hai_diem_km(toa_do[i], toa_do[i+1])
            phut_tho = (km_canh / tong_km) * phut_goc
            do_thi[a].append((b, phut_canh, km_canh, so_tuyen, phut_tho))
            do_thi[b].append((a, phut_canh, km_canh, so_tuyen, phut_tho))
            thong_tin_canh[(a,b,so_tuyen)] = (phut_canh, km_canh)
            thong_tin_canh[(b,a,so_tuyen)] = (phut_canh, km_canh)
    if not do_thi:
        return None
    # Chọn các nút đầu/cuối gần nhất trong mạng ứng viên.
    nut_dau = khoa_nut(cac_tuyen[0]['toa_do'][0])
    nut_cuoi = khoa_nut(cac_tuyen[0]['toa_do'][-1])
    if nut_dau not in do_thi or nut_cuoi not in do_thi:
        return None
    def heuristic(nut):
        # Hệ số 0.3 phút/km là ước lượng thấp để ưu tiên nút gần đích.
        return khoang_cach_hai_diem_km(nut, nut_cuoi) * 0.3
    hang_doi = [(heuristic(nut_dau), 0.0, nut_dau)]
    chi_phi_tot_nhat = {nut_dau: 0.0}
    truoc_do = {}
    while hang_doi:
        _, chi_phi_hien_tai, nut = heapq.heappop(hang_doi)
        if chi_phi_hien_tai != chi_phi_tot_nhat.get(nut):
            continue
        if nut == nut_cuoi:
            break
        for nut_ke, chi_phi_canh, km_canh, so_tuyen, phut_tho in do_thi.get(nut, []):
            moi = chi_phi_hien_tai + chi_phi_canh
            if moi < chi_phi_tot_nhat.get(nut_ke, float('inf')):
                chi_phi_tot_nhat[nut_ke] = moi
                truoc_do[nut_ke] = (nut, km_canh, chi_phi_canh, so_tuyen, phut_tho)
                heapq.heappush(hang_doi, (moi + heuristic(nut_ke), moi, nut_ke))
    if nut_cuoi not in chi_phi_tot_nhat:
        return None
    duong_di = [nut_cuoi]
    cac_canh = []
    while duong_di[-1] != nut_dau:
        thong_tin = truoc_do.get(duong_di[-1])
        if not thong_tin:
            return None
        nut_truoc, km_canh, phut_canh, so_tuyen, phut_tho = thong_tin
        cac_canh.append((km_canh, phut_canh, so_tuyen, phut_tho))
        duong_di.append(nut_truoc)
    duong_di.reverse()
    cac_canh.reverse()
    km = sum(c[0] for c in cac_canh)
    phut = sum(c[3] for c in cac_canh)
    # Nếu A* chỉ trả về đúng một trong các tuyến ban đầu, vẫn có thể dùng kết quả làm gợi ý thuật toán.
    return {'km': round(km, 2), 'phut': round(phut, 1), 'toa_do': [[n[0], n[1]] for n in duong_di],
            'la_tuyen_a_star': True, 'thuat_toan': 'A*', 'so_do_thi_nut': len(do_thi)}


@app.route('/api/route', methods=['POST'])  # Tạo API nhận yêu cầu tìm đường từ JavaScript.
def api_lo_trinh():  # Xử lý dữ liệu chuyến đi và trả kết quả dạng JSON.
    du_lieu = request.get_json(silent=True) or {}  # Đọc dữ liệu JSON gửi từ trình duyệt.
    diem_di = str(du_lieu.get('diem_di', '')).strip()  # Đọc và làm sạch địa chỉ xuất phát.
    diem_den = str(du_lieu.get('diem_den', '')).strip()  # Đọc và làm sạch địa chỉ đích đến.
    phuong_tien = str(du_lieu.get('phuong_tien', 'Xe máy'))  # Đọc phương tiện đã chọn.
    khung_gio = str(du_lieu.get('khung_gio', 'Ngay bây giờ'))  # Đọc khung giờ muốn tham khảo.
    try:  # Kiểm tra số hành khách do người dùng nhập.
        so_nguoi = max(1, min(50, int(du_lieu.get('so_nguoi', 1))))  # Giới hạn số hành khách từ 1 đến 50.
    except (TypeError, ValueError):  # Xử lý khi số hành khách không hợp lệ.
        so_nguoi = 1  # Dùng một hành khách làm giá trị mặc định.
    if not diem_di or not diem_den:  # Kiểm tra hai địa chỉ có được nhập đầy đủ không.
        return jsonify({'ok': False, 'loi': 'Bạn cần nhập cả điểm xuất phát và điểm đến.'}), 400  # Trả lỗi để giao diện hiển thị.
    if phuong_tien not in PHUONG_TIEN:  # Kiểm tra phương tiện có thuộc danh sách cho phép không.
        return jsonify({'ok': False, 'loi': 'Phương tiện không hợp lệ.'}), 400  # Từ chối dữ liệu phương tiện lạ.
    toa_do_di = tim_dia_diem(diem_di)  # Tìm tọa độ địa lý của điểm xuất phát.
    toa_do_den = tim_dia_diem(diem_den)  # Tìm tọa độ địa lý của điểm đến.
    if not toa_do_di or not toa_do_den:  # Kiểm tra dịch vụ định vị có tìm được cả hai nơi không.
        thieu = 'điểm xuất phát' if not toa_do_di and toa_do_den else ('điểm đến' if toa_do_di and not toa_do_den else 'cả điểm xuất phát và điểm đến')  # Xác định địa chỉ nào chưa định vị được.
        return jsonify({'ok': False, 'loi': f'Chưa xác định được {thieu}. Hãy chọn một địa chỉ trong danh sách gợi ý hoặc nhập tên đường + quận/huyện + TP.HCM. Ứng dụng đã thử hai dịch vụ tìm địa chỉ; nếu vẫn lỗi, hãy kiểm tra Internet rồi thử lại.'}), 404  # Báo lỗi cụ thể hơn.
    lo_trinh = None  # Khởi tạo biến chứa tuyến đường được chọn.
    cac_tuyen_osrm = lay_cac_lo_trinh(toa_do_di, toa_do_den) if phuong_tien != 'Máy bay' else []  # Lấy tối đa ba tuyến để so sánh khi dịch vụ hỗ trợ.
    cac_diem_ket_xe = doc_diem_ket_xe_mo_phong()  # Đọc điểm mô phỏng trước khi chấm điểm từng tuyến.
    # Nếu đã mô phỏng kẹt xe, chủ động tạo tuyến vòng qua các điểm trung gian quanh vùng kẹt xe.
    # Điều này bổ sung phương án né khi OSRM chỉ trả về một tuyến mặc định.
    cac_diem_dang_bat = [d for d in cac_diem_ket_xe if d.get('dang_bat', True)]
    if phuong_tien != 'Máy bay' and cac_diem_dang_bat:
        cac_tuyen_ne_tranh = tao_tuyen_ne_tranh_diem(toa_do_di, toa_do_den, cac_diem_dang_bat, gioi_han=8)
        # Gộp tuyến vòng tránh vào danh sách ứng viên và loại tuyến trùng theo khoảng cách/thời gian.
        for tuyen_vong in cac_tuyen_ne_tranh:
            if not any(abs(float(tuyen_vong['km']) - float(t['km'])) < 0.15 and abs(float(tuyen_vong['phut']) - float(t['phut'])) < 1 for t in cac_tuyen_osrm):
                cac_tuyen_osrm.append(tuyen_vong)
    # Chạy A* trên đồ thị ghép từ các tuyến ứng viên đã có để chọn đường có chi phí thấp.
    # Phạm vi tìm kiếm phụ thuộc vào các hình học tuyến do OSRM cung cấp.
    if phuong_tien != 'Máy bay' and cac_tuyen_osrm:
        ket_qua_a_star = tim_tuyen_bang_a_star(cac_tuyen_osrm, cac_diem_ket_xe, uoc_tinh_giao_thong(khung_gio)['he_so'])
        if ket_qua_a_star and not any(abs(ket_qua_a_star['km'] - float(t['km'])) < 0.1 and abs(ket_qua_a_star['phut'] - float(t['phut'])) < 1 for t in cac_tuyen_osrm):
            cac_tuyen_osrm.append(ket_qua_a_star)
    danh_sach_danh_gia = []  # Lưu thời gian và tác động của từng tuyến ứng viên.
    for chi_so, tuyen_ung_vien in enumerate(cac_tuyen_osrm, start=1):  # Duyệt các tuyến OSRM đã trả về.
        phat_mo_phong = sum(tinh_tac_dong_diem_ket_xe(tuyen_ung_vien.get('toa_do', []), diem) for diem in cac_diem_ket_xe)  # Ước tính số phút phạt do các vùng mô phỏng.
        danh_sach_danh_gia.append({'chi_so': chi_so, 'km': tuyen_ung_vien['km'], 'phut_goc': tuyen_ung_vien['phut'], 'phut_mo_phong': phat_mo_phong, 'phut_uoc_tinh': tuyen_ung_vien['phut'] * (uoc_tinh_giao_thong(khung_gio)['he_so']) + phat_mo_phong, 'toa_do': tuyen_ung_vien.get('toa_do', []), 'la_tuyen_ne_tranh': tuyen_ung_vien.get('la_tuyen_ne_tranh', False), 'la_tuyen_a_star': tuyen_ung_vien.get('la_tuyen_a_star', False), 'thuat_toan': tuyen_ung_vien.get('thuat_toan', 'OSRM')})  # Tính điểm thời gian tổng cho từng tuyến.
    if danh_sach_danh_gia:  # Nếu OSRM cung cấp ít nhất một tuyến.
        danh_gia_tot_nhat = min(danh_sach_danh_gia, key=lambda muc: muc['phut_uoc_tinh'])  # Chọn tuyến có thời gian ước tính thấp nhất sau khi tính kẹt xe mô phỏng.
        lo_trinh = cac_tuyen_osrm[danh_gia_tot_nhat['chi_so'] - 1]  # Lấy hình học tuyến được đánh giá tốt nhất.
        km = float(lo_trinh['km'])  # Lấy quãng đường của tuyến được chọn.
        phut_goc = float(lo_trinh['phut'])  # Lấy thời gian cơ bản của tuyến được chọn.
        toa_do_tuyen = lo_trinh.get('toa_do', [])  # Lấy tọa độ tuyến để vẽ trên bản đồ.
        nguon = 'OSRM/OpenStreetMap kết hợp A* trên đồ thị các tuyến ứng viên; không phải tìm kiếm trên toàn bộ mạng đường.'  # Ghi nguồn và việc so sánh phương án.
    else:  # Dùng khoảng cách dự phòng khi định tuyến thất bại hoặc chọn máy bay.
        km = khoang_cach_du_phong(toa_do_di, toa_do_den, phuong_tien)  # Ước lượng khoảng cách từ hai tọa độ.
        toc_do = {'Xe máy': 28, 'Ô tô cá nhân': 30, 'Taxi': 30, 'Xe buýt': 20, 'Máy bay': 650, 'Xe điện': 28}.get(phuong_tien, 28)  # Chọn tốc độ giả định cho phương tiện.
        phut_goc = km / toc_do * 60  # Tính thời gian cơ bản từ khoảng cách và tốc độ giả định.
        toa_do_tuyen = [list(toa_do_di), list(toa_do_den)]  # Vẽ đường thẳng nối hai điểm khi không có tuyến thực tế.
        nguon = 'Khoảng cách ước tính; không phải tuyến đường thực tế.'  # Cảnh báo về khoảng cách dự phòng.
    giao_thong = uoc_tinh_giao_thong(khung_gio)  # Lấy hệ số ùn tắc giả định theo khung giờ.
    if phuong_tien == 'Máy bay':  # Xử lý riêng máy bay vì không chịu ùn tắc đường bộ.
        nhan_giao_thong = 'Không áp dụng kẹt xe đường bộ'  # Hiển thị ghi chú phù hợp với máy bay.
        he_so = 1.0  # Không áp dụng hệ số kẹt xe cho máy bay.
        phut_goc += 150  # Cộng thời gian minh họa cho di chuyển và thủ tục sân bay.
    else:  # Xử lý các phương tiện di chuyển trên đường.
        nhan_giao_thong = giao_thong['nhan']  # Lấy nhãn tình trạng giao thông ước tính.
        he_so = giao_thong['he_so']  # Lấy hệ số thời gian giao thông.
    phut_cong_thuc = tinh_thoi_gian_co_ket_xe(phut_goc, he_so)  # Tính thời gian sau khi điều chỉnh theo hệ số giao thông.
    phut_du_doan, ghi_chu_model = du_doan_thoi_gian(km, phut_goc, he_so, phuong_tien)  # Dự đoán thời gian bằng mô hình Random Forest.
    if phuong_tien == 'Máy bay':  # Không dùng mô hình đường bộ để dự đoán thời gian bay.
        phut_du_doan = phut_goc  # Giữ thời gian bay minh họa cộng thủ tục sân bay.
    tac_dong_mo_phong = sum(tinh_tac_dong_diem_ket_xe(toa_do_tuyen, diem) for diem in cac_diem_ket_xe) if phuong_tien != 'Máy bay' else 0.0  # Cộng thời gian phạt của các vùng mô phỏng mà tuyến đi qua.
    phut_du_doan += tac_dong_mo_phong  # Điều chỉnh thời gian dự đoán theo kịch bản kẹt xe mô phỏng.
    if tac_dong_mo_phong > 0:  # Nếu tuyến chịu ảnh hưởng từ ít nhất một vùng mô phỏng.
        nhan_giao_thong += ' • Bị ảnh hưởng bởi kẹt xe mô phỏng'  # Gắn nhãn rõ để không nhầm với dữ liệu trực tiếp.
        ghi_chu_model += f' | Cộng thêm {tac_dong_mo_phong:.1f} phút do kịch bản mô phỏng, không phải dữ liệu giao thông thực.'  # Nêu nguồn của phần thời gian cộng thêm.
    chi_phi = tinh_chi_phi(km, phuong_tien, so_nguoi)  # Ước tính chi phí theo bảng công thức.
    ket_qua = {'ok': True, 'diem_di': diem_di, 'diem_den': diem_den, 'phuong_tien': phuong_tien, 'km': round(km, 2), 'phut': round(phut_du_doan, 1), 'phut_cong_thuc': round(phut_cong_thuc, 1), 'chi_phi': round(chi_phi), 'giao_thong': nhan_giao_thong, 'nguon': nguon, 'ghi_chu_model': ghi_chu_model, 'toa_do_di': list(toa_do_di), 'toa_do_den': list(toa_do_den), 'toa_do_tuyen': toa_do_tuyen, 'so_nguoi': so_nguoi, 'phut_mo_phong_cong_them': round(tac_dong_mo_phong, 1), 'so_diem_ket_xe_mo_phong': sum(1 for d in cac_diem_ket_xe if d.get('dang_bat', True)), 'cac_phuong_an_tuyen': [{'so_tuyen': m['chi_so'], 'km': round(m['km'], 2), 'phut_uoc_tinh': round(m['phut_uoc_tinh'], 1), 'phut_mo_phong': round(m['phut_mo_phong'], 1), 'la_tuyen_ne_tranh': m.get('la_tuyen_ne_tranh', False), 'la_tuyen_a_star': m.get('la_tuyen_a_star', False), 'thuat_toan': m.get('thuat_toan', 'OSRM'), 'toa_do': m.get('toa_do', [])} for m in danh_sach_danh_gia]}  # Đóng gói dữ liệu để giao diện sử dụng.
    os.makedirs(os.path.dirname(TEP_LICH_SU), exist_ok=True)  # Tạo thư mục history nếu chưa tồn tại.
    co_tep = os.path.exists(TEP_LICH_SU)  # Kiểm tra lịch sử đã được tạo trước đó chưa.
    with open(TEP_LICH_SU, 'a', newline='', encoding='utf-8-sig') as tep:  # Mở tệp lịch sử theo chế độ thêm.
        cot = ['Thời điểm', 'Điểm đi', 'Điểm đến', 'Phương tiện', 'Quãng đường km', 'Thời gian phút', 'Chi phí VNĐ', 'Giao thông']  # Định nghĩa cột lịch sử.
        ghi = csv.DictWriter(tep, fieldnames=cot)  # Tạo bộ ghi CSV với thứ tự cột cố định.
        if not co_tep:  # Kiểm tra đây là lần ghi đầu tiên.
            ghi.writeheader()  # Ghi hàng tiêu đề cho tệp CSV.
        ghi.writerow({'Thời điểm': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Điểm đi': diem_di, 'Điểm đến': diem_den, 'Phương tiện': phuong_tien, 'Quãng đường km': round(km, 2), 'Thời gian phút': round(phut_du_doan, 1), 'Chi phí VNĐ': round(chi_phi), 'Giao thông': nhan_giao_thong})  # Ghi kết quả chuyến đi.
    return jsonify(ket_qua)  # Trả dữ liệu tính toán về giao diện web.

def doc_diem_ket_xe_mo_phong():  # Đọc danh sách các điểm kẹt xe mô phỏng đã lưu.
    os.makedirs(os.path.dirname(TEP_KET_XE_MO_PHONG), exist_ok=True)  # Đảm bảo thư mục data tồn tại.
    if not os.path.exists(TEP_KET_XE_MO_PHONG):  # Kiểm tra tệp mô phỏng đã được tạo chưa.
        return []  # Trả về danh sách rỗng khi chưa có tình huống nào.
    try:  # Bắt lỗi nếu tệp JSON bị hỏng hoặc không đọc được.
        with open(TEP_KET_XE_MO_PHONG, 'r', encoding='utf-8') as tep:  # Mở tệp ở chế độ đọc.
            du_lieu = json.load(tep)  # Giải mã JSON thành dữ liệu Python.
        return du_lieu if isinstance(du_lieu, list) else []  # Chỉ chấp nhận cấu trúc danh sách.
    except (OSError, json.JSONDecodeError):  # Xử lý lỗi tệp hoặc JSON sai định dạng.
        return []  # Không làm sập ứng dụng khi dữ liệu mô phỏng bị lỗi.

def luu_diem_ket_xe_mo_phong(danh_sach):  # Ghi toàn bộ điểm mô phỏng xuống JSON.
    os.makedirs(os.path.dirname(TEP_KET_XE_MO_PHONG), exist_ok=True)  # Tạo thư mục data nếu chưa có.
    with open(TEP_KET_XE_MO_PHONG, 'w', encoding='utf-8') as tep:  # Mở tệp ở chế độ ghi đè.
        json.dump(danh_sach, tep, ensure_ascii=False, indent=2)  # Lưu JSON có dấu tiếng Việt và dễ đọc.

def khoang_cach_hai_diem_km(diem_a, diem_b):  # Tính khoảng cách Haversine giữa hai tọa độ.
    ban_kinh = 6371.0  # Bán kính trung bình Trái Đất theo kilomet.
    lat1, lon1 = map(math.radians, diem_a)  # Đổi tọa độ thứ nhất sang radian.
    lat2, lon2 = map(math.radians, diem_b)  # Đổi tọa độ thứ hai sang radian.
    dlat, dlon = lat2 - lat1, lon2 - lon1  # Tính độ chênh lệch vĩ độ và kinh độ.
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2  # Tính thành phần Haversine.
    return 2 * ban_kinh * math.asin(math.sqrt(min(1.0, a)))  # Trả về khoảng cách km.

def tinh_tac_dong_diem_ket_xe(toa_do_tuyen, diem_ket_xe):  # Ước lượng mức ảnh hưởng của một điểm mô phỏng lên tuyến.
    if not toa_do_tuyen or not diem_ket_xe.get('dang_bat', True):  # Bỏ qua tuyến rỗng hoặc điểm đã tắt.
        return 0.0  # Không cộng thêm thời gian.
    toa_do_ket_xe = (float(diem_ket_xe['vi_do']), float(diem_ket_xe['kinh_do']))  # Lấy tọa độ điểm ùn tắc.
    khoang_cach_nho_nhat = min(khoang_cach_hai_diem_km((float(d[0]), float(d[1])), toa_do_ket_xe) for d in toa_do_tuyen)  # Tìm điểm tuyến gần vùng ùn tắc nhất.
    ban_kinh = float(diem_ket_xe.get('ban_kinh_m', 500)) / 1000.0  # Đổi bán kính vùng ảnh hưởng từ mét sang km.
    if khoang_cach_nho_nhat > ban_kinh + 0.15:  # Nếu tuyến cách vùng mô phỏng quá xa thì không bị ảnh hưởng.
        return 0.0  # Không cộng thời gian cho tuyến không đi qua vùng đó.
    he_so_muc_do = {'nhe': 5, 'vua': 12, 'nang': 22}.get(diem_ket_xe.get('muc_do', 'vua'), 12)  # Thời gian phạt giả định theo mức độ.
    ty_le_chong_lan = max(0.15, min(1.0, 1.0 - max(0.0, khoang_cach_nho_nhat - ban_kinh) / 0.15))  # Giảm tác động khi tuyến nằm gần ngoài vùng ảnh hưởng.
    return he_so_muc_do * ty_le_chong_lan  # Trả số phút tăng thêm do kịch bản mô phỏng.

@app.route('/api/simulations/jams', methods=['GET', 'POST'])  # API đọc danh sách hoặc tạo điểm kẹt xe mô phỏng.
def api_diem_ket_xe_mo_phong():  # Quản lý điểm mô phỏng trên bản đồ.
    danh_sach = doc_diem_ket_xe_mo_phong()  # Nạp các điểm mô phỏng đã lưu.
    if request.method == 'GET':  # Nếu giao diện chỉ yêu cầu xem các điểm hiện có.
        return jsonify({'ok': True, 'jams': danh_sach, 'nguon': 'Dữ liệu mô phỏng do người dùng tạo; không phải giao thông trực tiếp.'})  # Trả danh sách và ghi rõ nguồn.
    du_lieu = request.get_json(silent=True) or {}  # Đọc dữ liệu điểm mô phỏng gửi lên.
    try:  # Kiểm tra tọa độ và bán kính nhập vào.
        vi_do = float(du_lieu['vi_do'])  # Đọc vĩ độ của điểm kẹt xe.
        kinh_do = float(du_lieu['kinh_do'])  # Đọc kinh độ của điểm kẹt xe.
        ban_kinh = int(du_lieu.get('ban_kinh_m', 500))  # Đọc bán kính vùng ảnh hưởng theo mét.
    except (KeyError, TypeError, ValueError):  # Xử lý dữ liệu thiếu hoặc sai kiểu.
        return jsonify({'ok': False, 'loi': 'Tọa độ hoặc bán kính không hợp lệ.'}), 400  # Trả lỗi dữ liệu cho giao diện.
    if not (-90 <= vi_do <= 90 and -180 <= kinh_do <= 180 and 100 <= ban_kinh <= 3000):  # Chặn tọa độ hoặc bán kính ngoài giới hạn.
        return jsonify({'ok': False, 'loi': 'Tọa độ không hợp lệ hoặc bán kính phải từ 100 đến 3000 mét.'}), 400  # Báo rõ giới hạn hợp lệ.
    muc_do = str(du_lieu.get('muc_do', 'vua'))  # Đọc mức độ kẹt xe.
    if muc_do not in ('nhe', 'vua', 'nang'):  # Chỉ cho phép ba mức độ được thiết kế.
        return jsonify({'ok': False, 'loi': 'Mức độ phải là nhe, vua hoặc nang.'}), 400  # Từ chối mức độ không hợp lệ.
    diem = {'id': uuid.uuid4().hex[:10], 'vi_do': vi_do, 'kinh_do': kinh_do, 'muc_do': muc_do, 'ban_kinh_m': ban_kinh, 'dang_bat': True, 'tao_luc': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  # Tạo bản ghi mô phỏng.
    danh_sach.append(diem)  # Thêm tình huống mới vào danh sách.
    luu_diem_ket_xe_mo_phong(danh_sach)  # Lưu để vẫn còn sau khi tải lại trang.
    return jsonify({'ok': True, 'jam': diem, 'jams': danh_sach})  # Trả điểm vừa tạo và danh sách cập nhật.

@app.route('/api/simulations/jams/<jam_id>', methods=['DELETE', 'PATCH'])  # API tắt/bật hoặc xóa một điểm mô phỏng.
def api_sua_diem_ket_xe_mo_phong(jam_id):  # Xử lý thay đổi trạng thái của điểm mô phỏng.
    danh_sach = doc_diem_ket_xe_mo_phong()  # Nạp danh sách hiện tại.
    diem = next((m for m in danh_sach if m.get('id') == jam_id), None)  # Tìm điểm theo mã.
    if diem is None:  # Kiểm tra mã điểm có tồn tại không.
        return jsonify({'ok': False, 'loi': 'Không tìm thấy điểm kẹt xe mô phỏng.'}), 404  # Trả lỗi nếu mã không tồn tại.
    if request.method == 'DELETE':  # Nếu người dùng chọn xóa điểm.
        danh_sach = [m for m in danh_sach if m.get('id') != jam_id]  # Loại điểm đó khỏi danh sách.
    else:  # Nếu người dùng chỉ muốn bật hoặc tắt điểm.
        du_lieu = request.get_json(silent=True) or {}  # Đọc trạng thái bật/tắt mới.
        diem['dang_bat'] = bool(du_lieu.get('dang_bat', not diem.get('dang_bat', True)))  # Cập nhật trạng thái.
    luu_diem_ket_xe_mo_phong(danh_sach)  # Lưu thay đổi vào tệp JSON.
    return jsonify({'ok': True, 'jams': danh_sach})  # Trả danh sách mới về trình duyệt.

@app.route('/api/simulations/jams/reset', methods=['POST'])  # API xóa toàn bộ tình huống kẹt xe mô phỏng.
def api_xoa_tat_ca_diem_mo_phong():  # Xử lý nút đặt lại mô phỏng.
    luu_diem_ket_xe_mo_phong([])  # Lưu danh sách rỗng để xóa mọi tình huống.
    return jsonify({'ok': True, 'jams': []})  # Báo đã đặt lại xong.

@app.route('/api/history')  # Khai báo API đọc lịch sử tìm đường.
def api_lich_su():  # Đọc các chuyến đi đã lưu từ CSV.
    if not os.path.exists(TEP_LICH_SU):  # Kiểm tra đã có tệp lịch sử chưa.
        return jsonify({'rows': []})  # Trả danh sách rỗng nếu chưa có lịch sử.
    with open(TEP_LICH_SU, 'r', newline='', encoding='utf-8-sig') as tep:  # Mở tệp lịch sử để đọc.
        dong = list(csv.DictReader(tep))  # Đọc các dòng CSV thành danh sách từ điển.
    return jsonify({'rows': dong[-30:][::-1]})  # Trả về tối đa 30 chuyến gần nhất theo thứ tự mới trước.

@app.route('/api/ml-lab', methods=['GET'])  # API chạy thực nghiệm các mô hình học máy trong phạm vi Chương 1-9.
def api_phong_thi_nghiem_ml():  # Trả bảng so sánh mô hình và độ đo đánh giá.
    try:  # Bắt lỗi huấn luyện hoặc tính độ đo.
        return jsonify(chay_thuc_nghiem())  # Chạy thí nghiệm và trả kết quả dạng JSON.
    except Exception as loi:  # Xử lý lỗi để giao diện hiển thị thông báo.
        return jsonify({'ok': False, 'loi': str(loi)}), 500  # Trả lỗi máy chủ.


if __name__ == '__main__':  # Chỉ chạy máy chủ khi gọi trực tiếp tệp app.py.
    app.run(host='127.0.0.1', port=5000, debug=False)  # Mở ứng dụng trên máy tính tại cổng 5000.
