# -*- coding: utf-8 -*-  # Cho phép ghi chú và chuỗi tiếng Việt trong tệp.
import csv  # Dùng để đọc và ghi lịch sử dưới định dạng CSV.
import math  # Dùng hàm lượng giác để tính khoảng cách địa lý.
import os  # Dùng để kiểm tra tệp lịch sử có tồn tại không.
import requests  # Gửi yêu cầu HTTP đến dịch vụ địa lý và định tuyến.

TEN_TEP_LICH_SU = "lich_su_lo_trinh.csv"  # Đặt tên tệp lưu lịch sử chuyến đi.

def tim_goi_y_dia_diem(dia_chi, gioi_han=5):  # Tìm địa chỉ qua hai dịch vụ địa lý dự phòng.
    """Ưu tiên Việt Nam/TP.HCM; thử Nominatim trước rồi Photon nếu dịch vụ đầu không phản hồi."""
    dia_chi = str(dia_chi or "").strip()  # Làm sạch nội dung tìm kiếm.
    if len(dia_chi) < 3:  # Không gửi truy vấn quá ngắn.
        return []  # Trả danh sách rỗng.
    cac_truy_van = [dia_chi]  # Thử đúng nội dung người dùng nhập.
    if "việt nam" not in dia_chi.lower() and "vietnam" not in dia_chi.lower():
        cac_truy_van.append(f"{dia_chi}, Việt Nam")  # Thêm quốc gia để tăng độ chính xác.
    if not any(x in dia_chi.lower() for x in ["hồ chí minh", "ho chi minh", "hcm", "sài gòn", "saigon"]):
        cac_truy_van.append(f"{dia_chi}, Thành phố Hồ Chí Minh, Việt Nam")  # Thử thêm TP.HCM.
    headers = {"User-Agent": "TrafficMindAI-StudentProject/1.2 (educational route planner)", "Accept-Language": "vi,en"}
    goi_y = []  # Danh sách địa chỉ tìm được.
    da_thay = set()  # Khử trùng kết quả.
    # Thử hai dịch vụ theo thứ tự; nếu một dịch vụ lỗi thì chuyển sang dịch vụ còn lại.
    for dich_vu in ("nominatim", "photon"):
        for truy_van in cac_truy_van:
            try:
                if dich_vu == "nominatim":
                    url = "https://nominatim.openstreetmap.org/search"
                    phan_hoi = requests.get(url, params={"q": truy_van, "format": "jsonv2", "limit": gioi_han, "countrycodes": "vn", "addressdetails": 1}, headers=headers, timeout=8)
                    phan_hoi.raise_for_status()
                    ket_qua = phan_hoi.json()
                    for muc in ket_qua:
                        ma = str(muc.get("place_id", muc.get("osm_id", "")))
                        if ma in da_thay: continue
                        da_thay.add(ma)
                        goi_y.append({"ten": muc.get("display_name", truy_van), "vi_do": float(muc["lat"]), "kinh_do": float(muc["lon"])})
                else:
                    url = "https://photon.komoot.io/api/"
                    phan_hoi = requests.get(url, params={"q": truy_van, "limit": gioi_han, "lang": "en"}, headers=headers, timeout=8)
                    phan_hoi.raise_for_status()
                    ket_qua = phan_hoi.json().get("features", [])
                    for muc in ket_qua:
                        props = muc.get("properties", {})
                        country = str(props.get("country", "")).lower()
                        if country and country not in ("vietnam", "viet nam"): continue
                        coords = muc.get("geometry", {}).get("coordinates", [])
                        if len(coords) < 2: continue
                        ma = str((props.get("osm_type"), props.get("osm_id"), coords))
                        if ma in da_thay: continue
                        da_thay.add(ma)
                        ten = ", ".join(str(props[k]) for k in ("name", "street", "district", "city", "state", "country") if props.get(k))
                        goi_y.append({"ten": ten or truy_van, "vi_do": float(coords[1]), "kinh_do": float(coords[0])})
                if goi_y: return goi_y[:gioi_han]  # Dừng ngay khi có kết quả hợp lệ.
            except (requests.RequestException, ValueError, KeyError, TypeError):
                continue  # Thử truy vấn hoặc dịch vụ dự phòng kế tiếp.
    return goi_y[:gioi_han]  # Không tự bịa tọa độ nếu cả hai dịch vụ đều thất bại.

def tim_dia_diem(dia_chi):  # Chuyển tên địa chỉ thành tọa độ địa lý.
    """Trả về tuple (vĩ độ, kinh độ), hoặc None nếu không tìm thấy địa điểm."""  # Mô tả kết quả của hàm.
    goi_y = tim_goi_y_dia_diem(dia_chi, gioi_han=1)  # Dùng bộ tìm kiếm có thử nhiều cách viết địa chỉ.
    if not goi_y:  # Kiểm tra có tìm thấy địa điểm nào không.
        return None  # Trả về None khi dịch vụ không tìm được địa chỉ.
    return goi_y[0]["vi_do"], goi_y[0]["kinh_do"]  # Trả về vĩ độ và kinh độ theo thứ tự thống nhất.

def lay_lo_trinh(diem_di, diem_den):  # Lấy tuyến đường bộ từ tọa độ điểm đi đến điểm đến.
    """Trả về quãng đường km, thời gian phút và các điểm tọa độ để vẽ bản đồ."""  # Mô tả cấu trúc kết quả.
    try:  # Bắt lỗi kết nối hoặc phản hồi dịch vụ định tuyến.
        toa_do_di = f"{diem_di[1]},{diem_di[0]}"  # Đổi tọa độ điểm đi sang thứ tự kinh độ,vĩ độ theo yêu cầu OSRM.
        toa_do_den = f"{diem_den[1]},{diem_den[0]}"  # Đổi tọa độ điểm đến sang thứ tự kinh độ,vĩ độ theo yêu cầu OSRM.
        url = f"https://router.project-osrm.org/route/v1/driving/{toa_do_di};{toa_do_den}"  # Tạo đường dẫn yêu cầu định tuyến đường bộ.
        phan_hoi = requests.get(url, params={"overview": "full", "geometries": "geojson", "alternatives": "true"}, timeout=20)  # Gửi yêu cầu lấy tuyến đường.
        phan_hoi.raise_for_status()  # Kiểm tra phản hồi HTTP.
        du_lieu = phan_hoi.json()  # Chuyển phản hồi thành dữ liệu Python.
        if du_lieu.get("code") != "Ok" or not du_lieu.get("routes"):  # Kiểm tra dịch vụ có trả tuyến đường hợp lệ không.
            return None  # Trả về None nếu không có tuyến.
        tuyen = du_lieu["routes"][0]  # Chọn tuyến đầu tiên do dịch vụ trả về.
        diem_ve = tuyen.get("geometry", {}).get("coordinates", [])  # Lấy danh sách điểm vẽ đường.
        toa_do_ve = [[vi_do, kinh_do] for kinh_do, vi_do in diem_ve]  # Đổi thứ tự tọa độ cho thư viện bản đồ Folium.
        return {"km": tuyen["distance"] / 1000, "phut": tuyen["duration"] / 60, "toa_do": toa_do_ve}  # Trả về khoảng cách, thời gian và hình học tuyến đường.
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):  # Bắt các lỗi truy vấn hoặc dữ liệu.
        return None  # Báo không lấy được tuyến đường.


def lay_cac_lo_trinh(diem_di, diem_den):  # Lấy nhiều phương án đường bộ từ OSRM khi dịch vụ hỗ trợ.
    """Trả danh sách tuyến thay thế; OSRM dùng thời gian đường bộ ước tính, không có dữ liệu kẹt xe trực tiếp."""  # Nêu giới hạn dữ liệu của dịch vụ.
    try:  # Bắt lỗi mạng hoặc phản hồi không hợp lệ.
        toa_do_di = f"{diem_di[1]},{diem_di[0]}"  # Chuyển điểm đi sang kinh độ,vĩ độ cho OSRM.
        toa_do_den = f"{diem_den[1]},{diem_den[0]}"  # Chuyển điểm đến sang kinh độ,vĩ độ cho OSRM.
        url = f"https://router.project-osrm.org/route/v1/driving/{toa_do_di};{toa_do_den}"  # Tạo URL định tuyến đường bộ.
        phan_hoi = requests.get(url, params={"overview": "full", "geometries": "geojson", "alternatives": "true", "steps": "false"}, timeout=20)  # Yêu cầu các tuyến thay thế nếu có.
        phan_hoi.raise_for_status()  # Kiểm tra mã HTTP.
        du_lieu = phan_hoi.json()  # Đọc phản hồi JSON.
        if du_lieu.get("code") != "Ok" or not du_lieu.get("routes"):  # Kiểm tra có tuyến hợp lệ.
            return []  # Trả danh sách rỗng khi không có tuyến.
        danh_sach = []  # Khởi tạo danh sách kết quả.
        for tuyen in du_lieu["routes"][:3]:  # Giới hạn tối đa ba phương án để giao diện dễ so sánh.
            toa_do = tuyen.get("geometry", {}).get("coordinates", [])  # Lấy hình học tuyến theo GeoJSON.
            danh_sach.append({"km": tuyen["distance"] / 1000, "phut": tuyen["duration"] / 60, "toa_do": [[vi_do, kinh_do] for kinh_do, vi_do in toa_do]})  # Chuẩn hóa tuyến về đơn vị km/phút và tọa độ Leaflet.
        return danh_sach  # Trả về các phương án đã chuẩn hóa.
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):  # Xử lý lỗi dịch vụ định tuyến.
        return []  # Cho phép ứng dụng dùng tuyến dự phòng.



def tao_tuyen_ne_tranh_diem(diem_di, diem_den, diem_ket_xe, gioi_han=8):
    """Tạo các tuyến vòng qua điểm trung gian quanh vùng kẹt xe để có phương án né khi OSRM chỉ trả một tuyến.
    Đây là tuyến đường vòng gợi ý theo mạng đường OSRM, không phải dữ liệu giao thông trực tiếp.
    """
    try:
        toa_do_di = f"{diem_di[1]},{diem_di[0]}"
        toa_do_den = f"{diem_den[1]},{diem_den[0]}"
        ung_vien = []
        for diem in diem_ket_xe:
            if not diem.get("dang_bat", True):
                continue
            lat = float(diem.get("vi_do", diem.get("lat", 0)))
            lon = float(diem.get("kinh_do", diem.get("lon", 0)))
            ban_kinh = float(diem.get("ban_kinh_m", diem.get("ban_kinh", 500)))
            # Đặt điểm trung gian ngoài rìa vùng kẹt xe, cộng biên an toàn 50%.
            r_m = max(250, ban_kinh * 1.5)
            dlat = r_m / 111000
            dlon = r_m / max(30000, 111000 * math.cos(math.radians(lat)))
            # Tạo tám hướng vòng tránh quanh điểm kẹt xe.
            for huong_lat, huong_lon in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
                wp_lat = lat + huong_lat * dlat
                wp_lon = lon + huong_lon * dlon
                ung_vien.append((wp_lat, wp_lon))
                if len(ung_vien) >= gioi_han:
                    break
            if len(ung_vien) >= gioi_han:
                break
        cac_tuyen = []
        for wp_lat, wp_lon in ung_vien:
            waypoint = f"{wp_lon},{wp_lat}"
            url = f"https://router.project-osrm.org/route/v1/driving/{toa_do_di};{waypoint};{toa_do_den}"
            try:
                phan_hoi = requests.get(url, params={"overview":"full","geometries":"geojson","steps":"false"}, timeout=12)
                phan_hoi.raise_for_status()
                du_lieu = phan_hoi.json()
                if du_lieu.get("code") != "Ok" or not du_lieu.get("routes"):
                    continue
                tuyen = du_lieu["routes"][0]
                coords = tuyen.get("geometry", {}).get("coordinates", [])
                if len(coords) < 2:
                    continue
                ket_qua = {"km": tuyen["distance"]/1000, "phut": tuyen["duration"]/60,
                           "toa_do": [[lat2, lon2] for lon2, lat2 in coords],
                           "la_tuyen_ne_tranh": True}
                # Loại tuyến trùng gần như hoàn toàn bằng cặp khoảng cách/thời gian.
                if not any(abs(x["km"]-ket_qua["km"]) < 0.15 and abs(x["phut"]-ket_qua["phut"]) < 1 for x in cac_tuyen):
                    cac_tuyen.append(ket_qua)
            except (requests.RequestException, ValueError, KeyError, TypeError):
                continue
        return cac_tuyen
    except (ValueError, TypeError, KeyError):
        return []

def khoang_cach_haversine(diem_di, diem_den):  # Tính khoảng cách đường chim bay giữa hai tọa độ.
    """Dùng công thức Haversine để tính khoảng cách địa lý theo kilomet."""  # Mô tả công thức được sử dụng.
    vi1, kinh1 = map(math.radians, diem_di)  # Đổi vĩ độ và kinh độ điểm đi sang radian.
    vi2, kinh2 = map(math.radians, diem_den)  # Đổi vĩ độ và kinh độ điểm đến sang radian.
    d_vi = vi2 - vi1  # Tính chênh lệch vĩ độ.
    d_kinh = kinh2 - kinh1  # Tính chênh lệch kinh độ.
    a = math.sin(d_vi / 2) ** 2 + math.cos(vi1) * math.cos(vi2) * math.sin(d_kinh / 2) ** 2  # Tính thành phần trung gian của Haversine.
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, a)))  # Tính khoảng cách cung tròn lớn theo bán kính Trái Đất.

def khoang_cach_du_phong(diem_di, diem_den, phuong_tien):  # Ước lượng khoảng cách khi không lấy được tuyến đường.
    """Đây chỉ là ước tính; không thay thế quãng đường thực tế trên bản đồ."""  # Nêu giới hạn của hàm.
    khoang_cach_thang = khoang_cach_haversine(diem_di, diem_den)  # Tính khoảng cách đường chim bay.
    if phuong_tien == "Máy bay":  # Kiểm tra người dùng chọn máy bay.
        return khoang_cach_thang * 1.08  # Thêm hệ số ước lượng đường bay.
    return khoang_cach_thang * 1.30  # Thêm hệ số đường bộ gần đúng.

def luu_lich_su(ban_ghi):  # Thêm kết quả một chuyến đi vào tệp lịch sử.
    """Tạo tiêu đề cột khi cần và ghi bản ghi chuyến đi vào cuối tệp."""  # Mô tả tác dụng lưu trữ.
    da_co_tep = os.path.exists(TEN_TEP_LICH_SU)  # Kiểm tra tệp lịch sử đã tồn tại chưa.
    with open(TEN_TEP_LICH_SU, "a", newline="", encoding="utf-8-sig") as tep:  # Mở tệp theo chế độ thêm và hỗ trợ tiếng Việt.
        bo_ghi = csv.DictWriter(tep, fieldnames=list(ban_ghi.keys()))  # Tạo đối tượng ghi dữ liệu theo tên cột.
        if not da_co_tep:  # Kiểm tra đây có phải lần tạo tệp đầu tiên không.
            bo_ghi.writeheader()  # Ghi tiêu đề cột.
        bo_ghi.writerow(ban_ghi)  # Ghi dữ liệu chuyến đi vào tệp.

def doc_lich_su():  # Đọc tệp lịch sử thành bảng dữ liệu.
    """Trả về DataFrame rỗng nếu chưa có tệp hoặc tệp không đọc được."""  # Mô tả giá trị trả về.
    import pandas as pd  # Nhập Pandas để tạo bảng dữ liệu.
    if not os.path.exists(TEN_TEP_LICH_SU):  # Kiểm tra tệp lịch sử có tồn tại không.
        return pd.DataFrame()  # Trả về bảng rỗng nếu chưa có chuyến đi.
    try:  # Bắt lỗi khi đọc CSV.
        return pd.read_csv(TEN_TEP_LICH_SU, encoding="utf-8-sig")  # Đọc lịch sử và giữ đúng mã tiếng Việt.
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):  # Xử lý lỗi hệ thống tệp hoặc định dạng CSV.
        return pd.DataFrame()  # Trả về bảng rỗng để giao diện không bị lỗi.
