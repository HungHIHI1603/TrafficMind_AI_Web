// Lưu đối tượng bản đồ, lớp tuyến đường và dữ liệu chuyến đi mới nhất.
let map; // Khai báo bản đồ Leaflet.
let routeLayer; // Lưu lớp đường đi để có thể xóa khi tìm tuyến mới.
let latestTrip = null; // Lưu kết quả mới nhất để so sánh phương tiện.

function initMap() { // Khởi tạo bản đồ khi trang tải xong.
  map = L.map('map').setView([10.7769, 106.7009], 12); // Đặt tâm bản đồ ban đầu tại TP. Hồ Chí Minh.
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map); // Nạp các ô bản đồ OpenStreetMap.
} // Kết thúc hàm khởi tạo bản đồ.

function showMessage(text, error = false) { // Hiển thị thông báo cho người dùng.
  const box = document.getElementById('message'); // Lấy vùng thông báo trên trang.
  box.textContent = text; // Gán nội dung thông báo an toàn dưới dạng văn bản.
  box.classList.remove('hidden', 'error'); // Hiện thông báo và xóa trạng thái cũ.
  if (error) box.classList.add('error'); // Thêm màu đỏ nếu là thông báo lỗi.
} // Kết thúc hàm hiển thị thông báo.

function phatCanhBaoKetXe() { // Phát tiếng bíp ngắn để báo khi tuyến bị ảnh hưởng bởi kẹt xe mô phỏng.
  try { // Trình duyệt có thể chặn âm thanh nếu chưa có thao tác của người dùng.
    const AudioContextClass = window.AudioContext || window.webkitAudioContext; // Hỗ trợ tên AudioContext trên các trình duyệt phổ biến.
    if (!AudioContextClass) return; // Bỏ qua âm thanh nếu trình duyệt không hỗ trợ.
    const amThanh = new AudioContextClass(); // Tạo bộ phát âm thanh đơn giản không cần tệp ngoài.
    const daoDong = amThanh.createOscillator(); // Tạo nguồn âm dạng sóng.
    const amLuong = amThanh.createGain(); // Tạo bộ điều chỉnh âm lượng.
    daoDong.frequency.value = 880; // Đặt tần số tiếng bíp cao dễ nhận biết.
    amLuong.gain.value = 0.08; // Giữ âm lượng nhỏ để không gây giật mình.
    daoDong.connect(amLuong); amLuong.connect(amThanh.destination); // Nối nguồn âm qua bộ âm lượng tới loa.
    daoDong.start(); daoDong.stop(amThanh.currentTime + 0.18); // Phát tiếng bíp trong 0,18 giây.
    daoDong.onended = () => amThanh.close(); // Giải phóng tài nguyên âm thanh khi kết thúc.
  } catch (loi) { console.info('Trình duyệt không cho phát tiếng bíp:', loi); } // Không làm hỏng tính năng tìm đường nếu âm thanh bị chặn.
} // Kết thúc hàm phát cảnh báo.

function formatMoney(value) { // Định dạng tiền Việt Nam dễ đọc.
  return new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(value) + ' ₫'; // Trả về số tiền có dấu phân cách hàng nghìn.
} // Kết thúc hàm định dạng tiền.

function drawRoute(data) { // Vẽ điểm xuất phát, điểm đến và tuyến đường trên bản đồ.
  if (routeLayer) map.removeLayer(routeLayer); // Xóa tuyến cũ nếu người dùng tìm đường lần nữa.
  const group = []; // Tạo nhóm để gom các điểm và đường mới.
  L.marker(data.toa_do_di).bindPopup('Điểm xuất phát').addTo(map); // Thêm điểm đánh dấu xuất phát.
  L.marker(data.toa_do_den).bindPopup('Điểm đến').addTo(map); // Thêm điểm đánh dấu điểm đến.
  if (data.toa_do_tuyen && data.toa_do_tuyen.length > 1) { // Kiểm tra có tọa độ để vẽ tuyến đường không.
    group.push(L.polyline(data.toa_do_tuyen, { color: '#4778f5', weight: 5, opacity: 0.9 }).addTo(map)); // Vẽ tuyến đường màu xanh.
  } // Kết thúc kiểm tra hình học tuyến.
  group.push(L.marker(data.toa_do_di)); // Đưa tọa độ xuất phát vào nhóm căn khung bản đồ.
  group.push(L.marker(data.toa_do_den)); // Đưa tọa độ đích đến vào nhóm căn khung bản đồ.
  routeLayer = L.featureGroup(group).addTo(map); // Lưu lớp mới để quản lý tuyến đường.
  map.fitBounds(routeLayer.getBounds().pad(0.12)); // Tự căn bản đồ để nhìn thấy toàn bộ hành trình.
} // Kết thúc hàm vẽ tuyến đường.

document.getElementById('route-form').addEventListener('submit', async (event) => { // Xử lý khi người dùng gửi biểu mẫu.
  event.preventDefault(); // Ngăn trình duyệt tải lại trang theo cách mặc định.
  const button = document.getElementById('submit-btn'); // Lấy nút tìm đường.
  button.disabled = true; // Khóa nút để tránh gửi nhiều yêu cầu cùng lúc.
  button.textContent = 'Đang phân tích lộ trình…'; // Hiển thị trạng thái đang xử lý.
  document.getElementById('message').classList.add('hidden'); // Ẩn thông báo cũ.
  const payload = { diem_di: document.getElementById('diem_di').value, diem_den: document.getElementById('diem_den').value, phuong_tien: document.getElementById('phuong_tien').value, so_nguoi: document.getElementById('so_nguoi').value, khung_gio: document.getElementById('khung_gio').value }; // Thu thập dữ liệu từ biểu mẫu.
  try { // Bắt lỗi mạng hoặc lỗi máy chủ.
    const response = await fetch('/api/route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); // Gửi yêu cầu đến API Python.
    const data = await response.json(); // Chuyển phản hồi JSON thành đối tượng JavaScript.
    if (!response.ok || !data.ok) throw new Error(data.loi || 'Không thể tính lộ trình.'); // Hiển thị lỗi nếu máy chủ trả kết quả không thành công.
    latestTrip = data; // Lưu chuyến đi để dùng ở trang so sánh.
    document.getElementById('metric-km').textContent = data.km.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' km'; // Hiển thị quãng đường.
    document.getElementById('metric-time').textContent = Math.round(data.phut) + ' phút'; // Hiển thị thời gian dự đoán.
    document.getElementById('metric-cost').textContent = formatMoney(data.chi_phi); // Hiển thị chi phí ước tính.
    document.getElementById('metric-traffic').textContent = data.giao_thong; // Hiển thị nhãn giao thông.
    const soPhuongAn = (data.cac_phuong_an_tuyen || []).length; // Đếm số tuyến OSRM trả về để so sánh.
    document.getElementById('route-source').textContent = 'Nguồn khoảng cách: ' + data.nguon + (soPhuongAn ? ` Có ${soPhuongAn} phương án tuyến được chấm điểm: ` + data.cac_phuong_an_tuyen.map(m => `Tuyến ${m.so_tuyen}: ${m.km} km, khoảng ${m.phut_uoc_tinh} phút (mô phỏng +${m.phut_mo_phong} phút)`).join('; ') : ' Dịch vụ không trả tuyến thay thế trong lần này.'); // Hiển thị nguồn và tóm tắt từng phương án để người dùng đối chiếu.
    document.getElementById('model-note').textContent = 'Mô hình: ' + data.ghi_chu_model; // Hiển thị ghi chú về mô hình học máy.
    document.getElementById('formula-time').textContent = 'Thời gian theo công thức hệ số giao thông: ' + data.phut_cong_thuc + ' phút. Thời gian mô phỏng cộng thêm: ' + (data.phut_mo_phong_cong_them || 0) + ' phút.'; // Hiển thị thời gian theo công thức và phần mô phỏng riêng biệt.
    if ((data.phut_mo_phong_cong_them || 0) > 0) { showMessage(`Cảnh báo: tuyến đang bị ảnh hưởng bởi kẹt xe MÔ PHỎNG, cộng khoảng ${data.phut_mo_phong_cong_them} phút.`, true); phatCanhBaoKetXe(); } // Báo trực quan và phát tiếng bíp khi tuyến bị ảnh hưởng.
    document.getElementById('results').classList.remove('hidden'); // Hiện khu vực kết quả.
    drawRoute(data); // Cập nhật bản đồ theo tuyến mới.
    renderRouteAlternatives(data); // Hiện các tuyến khác để người dùng có thể chọn và xem đường đi.
    showMessage('Đã tính xong lộ trình và lưu kết quả vào lịch sử.'); // Báo người dùng kết quả đã sẵn sàng.
  } catch (error) { // Xử lý lỗi khi tìm địa chỉ hoặc kết nối dịch vụ.
    showMessage(error.message || 'Đã xảy ra lỗi không xác định.', true); // Hiển thị thông báo lỗi thân thiện.
  } finally { // Luôn khôi phục trạng thái nút sau khi xử lý.
    button.disabled = false; // Cho phép bấm nút lần nữa.
    button.innerHTML = 'Tìm lộ trình <span>→</span>'; // Khôi phục nội dung nút.
  } // Kết thúc khối xử lý cuối cùng.
}); // Kết thúc sự kiện gửi biểu mẫu.


function renderRouteAlternatives(data) { // Hiển thị các phương án tuyến và cho phép chọn tuyến khác.
  const box = document.getElementById('route-alternatives'); // Lấy khu vực danh sách tuyến.
  const routes = data.cac_phuong_an_tuyen || []; // Lấy danh sách tuyến máy chủ đã chấm điểm.
  if (!routes.length) { box.innerHTML = '<h3>Gợi ý tuyến đường khác</h3><p>Chưa có phương án đường bộ thay thế từ dịch vụ định tuyến. Hãy đặt điểm kẹt xe mô phỏng rồi tìm lại để hệ thống thử tạo tuyến vòng tránh.</p>'; return; }
  box.innerHTML = '<h3>Gợi ý tuyến đường khác</h3><p>Chọn một phương án để xem đường trên bản đồ. Thời gian có cộng phần phạt mô phỏng nếu tuyến đi qua vùng kẹt xe.</p>';
  routes.forEach((route, index) => { // Tạo một nút cho từng phương án.
    const button = document.createElement('button'); // Dùng DOM API để tránh chèn nội dung không an toàn.
    button.type = 'button'; // Không gửi biểu mẫu khi chọn tuyến.
    button.className = 'route-option'; // Áp dụng kiểu giao diện cho thẻ tuyến.
    const tag = route.la_tuyen_a_star ? ' • A* đề xuất' : (route.la_tuyen_ne_tranh ? ' • Tuyến vòng tránh' : (index === 0 ? ' • Tuyến đề xuất' : ' • Tuyến thay thế'));
    button.textContent = `Tuyến ${index + 1}${tag} — ${route.km} km — khoảng ${Math.round(route.phut_uoc_tinh)} phút (kẹt xe mô phỏng +${route.phut_mo_phong} phút)`;
    button.addEventListener('click', () => { // Khi chọn, vẽ đúng tuyến đó lên bản đồ.
      if (routeLayer) map.removeLayer(routeLayer); // Xóa tuyến đang hiển thị.
      const coords = route.toa_do || []; // Lấy tọa độ tuyến được chọn.
      if (coords.length > 1) {
        routeLayer = L.polyline(coords, { color: route.la_tuyen_ne_tranh ? '#0d9f6e' : '#4778f5', weight: 6, opacity: 0.95 }).addTo(map); // Vẽ tuyến vòng tránh màu xanh lá.
        map.fitBounds(routeLayer.getBounds().pad(0.12)); // Căn bản đồ theo tuyến được chọn.
      }
      document.getElementById('metric-km').textContent = route.km.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' km'; // Cập nhật quãng đường theo phương án.
      document.getElementById('metric-time').textContent = Math.round(route.phut_uoc_tinh) + ' phút'; // Cập nhật thời gian ước tính theo phương án.
      showMessage(`Đã chọn Tuyến ${index + 1}${tag}. Hãy quan sát đường được tô trên bản đồ.`); // Xác nhận tuyến đã chọn.
      box.querySelectorAll('.route-option').forEach(item => item.classList.remove('selected')); // Bỏ trạng thái chọn cũ.
      button.classList.add('selected'); // Đánh dấu phương án đang xem.
    });
    box.appendChild(button); // Thêm nút tuyến vào danh sách.
  });
} // Kết thúc hàm hiển thị phương án tuyến.

document.getElementById('swap-btn').addEventListener('click', () => { // Xử lý thao tác đổi điểm đi và đến.
  const start = document.getElementById('diem_di'); // Lấy ô điểm xuất phát.
  const end = document.getElementById('diem_den'); // Lấy ô điểm đến.
  [start.value, end.value] = [end.value, start.value]; // Hoán đổi hai giá trị địa chỉ.
}); // Kết thúc sự kiện đổi địa chỉ.

function activatePanel(name) { // Chuyển đổi các trang chức năng trong ứng dụng.
  document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active-panel')); // Ẩn tất cả các trang.
  document.getElementById(name + '-panel').classList.add('active-panel'); // Hiện trang được chọn.
  document.querySelectorAll('.nav-item').forEach(button => button.classList.toggle('active', button.dataset.panel === name)); // Cập nhật nút điều hướng đang được chọn.
  if (name === 'compare') renderComparison(); // Cập nhật bảng so sánh khi mở trang này.
  if (name === 'history') loadHistory(); // Tải lịch sử khi mở trang này.
  if (name === 'route') setTimeout(() => map.invalidateSize(), 80); // Sửa kích thước bản đồ khi quay lại trang tìm đường.
} // Kết thúc hàm chuyển trang.

document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => activatePanel(button.dataset.panel))); // Gắn sự kiện cho các nút điều hướng.
document.querySelectorAll('.back-route').forEach(button => button.addEventListener('click', () => activatePanel('route'))); // Cho phép quay lại tìm đường từ trang so sánh.

function renderComparison() { // Tạo bảng so sánh chi phí của các phương tiện.
  const target = document.getElementById('compare-table'); // Lấy vùng chứa bảng so sánh.
  if (!latestTrip) { target.innerHTML = '<p>Chưa có dữ liệu. Hãy tìm một lộ trình trước.</p>'; return; } // Dừng nếu chưa có chuyến đi để so sánh.
  const rates = { 'Xe máy': 1200, 'Ô tô cá nhân': 4500, 'Taxi': 14000, 'Xe buýt': 0, 'Máy bay': 1800, 'Xe điện': 700 }; // Khai báo giá/km minh họa để so sánh nhanh.
  const base = { 'Xe máy': 0, 'Ô tô cá nhân': 0, 'Taxi': 12000, 'Xe buýt': 10000, 'Máy bay': 900000, 'Xe điện': 0 }; // Khai báo phí cơ bản giả định.
  const passenger = latestTrip.so_nguoi; // Lấy số hành khách của chuyến đi vừa tính.
  const names = ['Xe máy', 'Ô tô cá nhân', 'Taxi', 'Xe buýt', 'Máy bay', 'Xe điện']; // Liệt kê phương tiện cần so sánh.
  const rows = names.map(name => { const price = name === 'Xe buýt' ? passenger * 10000 : base[name] + latestTrip.km * rates[name]; const note = name === 'Máy bay' ? 'Khoảng cách đường bay chỉ ước tính' : name === 'Xe buýt' ? 'Chưa xác nhận tuyến và lịch xe' : 'Ước tính theo quãng đường'; return `<tr><td>${name}</td><td>${latestTrip.km.toFixed(1)} km*</td><td>${formatMoney(price)}</td><td>${note}</td></tr>`; }).join(''); // Tạo các hàng bảng theo công thức ước tính.
  target.innerHTML = `<table><thead><tr><th>Phương tiện</th><th>Khoảng cách tham khảo</th><th>Chi phí tham khảo</th><th>Ghi chú</th></tr></thead><tbody>${rows}</tbody></table><p>* Bảng này dùng cùng khoảng cách chuyến đi gần nhất để so sánh chi phí sơ bộ; không phải tuyến thực tế của từng loại phương tiện.</p>`; // Hiển thị bảng và giải thích giới hạn so sánh.
} // Kết thúc hàm so sánh.

async function loadHistory() { // Lấy lịch sử chuyến đi từ máy chủ Python.
  const target = document.getElementById('history-table'); // Lấy vùng chứa bảng lịch sử.
  target.textContent = 'Đang tải lịch sử…'; // Hiển thị trạng thái chờ.
  try { // Bắt lỗi khi máy chủ không trả dữ liệu.
    const response = await fetch('/api/history'); // Gọi API đọc lịch sử.
    const data = await response.json(); // Đọc JSON chứa các dòng lịch sử.
    if (!data.rows.length) { target.textContent = 'Chưa có lịch sử tìm đường.'; return; } // Hiển thị thông báo khi chưa có chuyến đi.
    const cols = Object.keys(data.rows[0]); // Lấy tên cột từ bản ghi đầu tiên.
    const head = cols.map(col => `<th>${col}</th>`).join(''); // Tạo hàng tiêu đề của bảng.
    const body = data.rows.map(row => `<tr>${cols.map(col => `<td>${String(row[col] ?? '')}</td>`).join('')}</tr>`).join(''); // Tạo các hàng dữ liệu lịch sử.
    target.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`; // Hiển thị bảng lịch sử.
  } catch (error) { target.textContent = 'Không thể tải lịch sử lúc này.'; } // Hiển thị thông báo nếu API gặp lỗi.
} // Kết thúc hàm tải lịch sử.
document.getElementById('refresh-history').addEventListener('click', loadHistory); // Gắn sự kiện làm mới lịch sử.

initMap(); // Khởi tạo bản đồ khi tải xong mã JavaScript.

// Gắn gợi ý địa chỉ trực tuyến cho cả điểm xuất phát và điểm đến.
function ganGoiYDiaChi(idInput, idDanhSach) { // Cấu hình tính năng gợi ý cho một ô địa chỉ.
  const oNhap = document.getElementById(idInput); // Lấy ô nhập địa chỉ theo mã HTML.
  const danhSach = document.getElementById(idDanhSach); // Lấy danh sách gợi ý tương ứng.
  let boHenGio = null; // Lưu bộ hẹn giờ để tránh gửi yêu cầu sau mỗi phím bấm.
  let truyVanCuoi = ''; // Ghi nhớ truy vấn đã gửi gần nhất để tránh gọi lặp.
  oNhap.addEventListener('input', () => { // Theo dõi khi người dùng nhập hoặc sửa địa chỉ.
    window.clearTimeout(boHenGio); // Hủy yêu cầu chờ cũ nếu người dùng tiếp tục gõ.
    const truyVan = oNhap.value.trim(); // Lấy nội dung địa chỉ hiện tại và bỏ khoảng trắng thừa.
    if (truyVan.length < 3 || truyVan === truyVanCuoi) return; // Không tìm khi quá ngắn hoặc không đổi nội dung.
    boHenGio = window.setTimeout(async () => { // Chờ một chút để giảm số yêu cầu gửi đi.
      truyVanCuoi = truyVan; // Ghi nhận truy vấn đang được xử lý.
      try { // Bắt lỗi mạng trong lúc lấy gợi ý.
        const phanHoi = await fetch('/api/geocode?q=' + encodeURIComponent(truyVan)); // Gửi từ khóa đã mã hóa lên API Python.
        if (!phanHoi.ok) return; // Bỏ qua nếu máy chủ trả về lỗi.
        const duLieu = await phanHoi.json(); // Chuyển dữ liệu phản hồi thành JSON.
        danhSach.replaceChildren(); // Xóa gợi ý cũ để không trộn với kết quả mới.
        (duLieu.results || []).forEach((muc) => { // Duyệt danh sách địa chỉ tìm được.
          const luaChon = document.createElement('option'); // Tạo một lựa chọn cho danh sách gợi ý.
          luaChon.value = muc.ten; // Đặt tên địa điểm làm nội dung có thể chọn.
          danhSach.appendChild(luaChon); // Thêm lựa chọn vào danh sách gợi ý của ô nhập.
        }); // Kết thúc duyệt các địa chỉ.
      } catch (error) { // Xử lý lỗi kết nối mà không làm hỏng biểu mẫu.
        console.warn('Không tải được gợi ý địa chỉ:', error); // Ghi thông tin kỹ thuật để dễ kiểm tra trong Console.
      } // Kết thúc xử lý lỗi.
    }, 450); // Chờ 450 mili giây sau khi người dùng ngừng gõ.
  }); // Kết thúc sự kiện nhập địa chỉ.
} // Kết thúc hàm cấu hình gợi ý địa chỉ.

ganGoiYDiaChi('diem_di', 'goi-y-diem-di'); // Bật gợi ý cho điểm xuất phát.
ganGoiYDiaChi('diem_den', 'goi-y-diem-den'); // Bật gợi ý cho điểm đến.

// ====================== MÔ PHỎNG KẸT XE ======================
let dangDatDiemKetXe = false; // Ghi nhớ người dùng có đang ở chế độ đặt điểm trên bản đồ không.
let cacDiemMoPhong = []; // Lưu danh sách điểm mô phỏng đã tải từ máy chủ.
let lopDiemMoPhong = L.featureGroup(); // Gom các vòng tròn và dấu kẹt xe để dễ cập nhật.
let viTriMoPhongTam = null; // Lưu tọa độ tạm khi chọn điểm bằng cách bấm bản đồ.

function hienThiTrangThaiMoPhong(noiDung, loi = false) { // Hiển thị kết quả thao tác mô phỏng.
  const o = document.getElementById('jam-status'); // Lấy vùng trạng thái của công cụ mô phỏng.
  o.textContent = noiDung; // Hiển thị thông báo dưới dạng văn bản an toàn.
  o.style.background = loi ? '#fff0f0' : '#eef4ff'; // Đổi nền đỏ nhạt khi có lỗi.
  o.style.color = loi ? '#b63d3d' : '#3e62b8'; // Đổi màu chữ theo trạng thái.
} // Kết thúc hàm trạng thái mô phỏng.

function tenMucDo(mucDo) { // Chuyển mã mức độ thành nhãn tiếng Việt.
  return ({ nhe: 'Nhẹ', vua: 'Vừa', nang: 'Nặng' })[mucDo] || 'Vừa'; // Trả nhãn phù hợp.
} // Kết thúc hàm đổi nhãn mức độ.

function veCacDiemMoPhong() { // Vẽ toàn bộ vùng kẹt xe mô phỏng lên bản đồ.
  lopDiemMoPhong.clearLayers(); // Xóa các vùng cũ trước khi vẽ lại.
  cacDiemMoPhong.forEach((diem) => { // Duyệt từng điểm mô phỏng đã lưu.
    if (!diem.dang_bat) return; // Không vẽ vùng đang tắt.
    const mau = diem.muc_do === 'nang' ? '#df3030' : diem.muc_do === 'vua' ? '#f08a24' : '#e5b72d'; // Chọn màu theo mức độ.
    L.circle([diem.vi_do, diem.kinh_do], { radius: diem.ban_kinh_m, color: mau, fillColor: mau, fillOpacity: 0.18, weight: 2 }).bindPopup(`<b>Kẹt xe mô phỏng: ${tenMucDo(diem.muc_do)}</b><br>Bán kính: ${diem.ban_kinh_m} m<br>Thời điểm tạo: ${diem.tao_luc}<br><small>Dữ liệu giả lập, không phải giao thông trực tiếp.</small>`).addTo(lopDiemMoPhong); // Vẽ vùng ảnh hưởng và thông tin chi tiết.
    L.marker([diem.vi_do, diem.kinh_do], { icon: L.divIcon({ className: 'jam-marker', iconSize: [16, 16], iconAnchor: [8, 8] }) }).bindTooltip(`Kẹt xe ${tenMucDo(diem.muc_do).toLowerCase()}`).addTo(lopDiemMoPhong); // Đánh dấu tâm điểm kẹt xe.
  }); // Kết thúc vòng lặp vẽ điểm.
} // Kết thúc hàm vẽ vùng mô phỏng.

function hienThiDanhSachMoPhong() { // Tạo danh sách điểm để người dùng bật, tắt hoặc xóa.
  const khung = document.getElementById('jam-list'); // Lấy vùng danh sách điểm.
  if (!cacDiemMoPhong.length) { khung.textContent = 'Chưa có điểm mô phỏng nào.'; return; } // Hiển thị hướng dẫn khi danh sách trống.
  khung.replaceChildren(); // Xóa nội dung danh sách cũ.
  cacDiemMoPhong.forEach((diem) => { // Duyệt các điểm mô phỏng.
    const muc = document.createElement('div'); // Tạo thẻ cho một điểm.
    muc.className = 'jam-item' + (diem.dang_bat ? '' : ' disabled-jam'); // Làm mờ điểm đang tắt.
    const thongTin = document.createElement('div'); // Tạo vùng văn bản thông tin.
    const toaDo = `${Number(diem.vi_do).toFixed(5)}, ${Number(diem.kinh_do).toFixed(5)}`; // Định dạng tọa độ ngắn gọn.
    thongTin.innerHTML = `<strong>Kẹt xe ${tenMucDo(diem.muc_do)} · ${diem.ban_kinh_m} m</strong><span>${toaDo} · ${diem.dang_bat ? 'Đang bật' : 'Đang tắt'}</span>`; // Hiển thị mức độ, tọa độ và trạng thái.
    const cacNut = document.createElement('div'); // Tạo vùng các nút thao tác.
    cacNut.className = 'jam-controls'; // Áp dụng kiểu nút theo CSS.
    const nutBatTat = document.createElement('button'); // Tạo nút bật hoặc tắt điểm.
    nutBatTat.textContent = diem.dang_bat ? 'Tắt điểm' : 'Bật điểm'; // Đặt nhãn theo trạng thái hiện tại.
    nutBatTat.addEventListener('click', () => capNhatTrangThaiDiem(diem)); // Gắn thao tác bật/tắt điểm.
    const nutXoa = document.createElement('button'); // Tạo nút xóa điểm.
    nutXoa.textContent = 'Xóa'; // Đặt nhãn xóa.
    nutXoa.addEventListener('click', () => xoaDiemMoPhong(diem.id)); // Gắn thao tác xóa điểm này.
    cacNut.append(nutBatTat, nutXoa); // Thêm hai nút vào thẻ.
    muc.append(thongTin, cacNut); // Ghép thông tin và nút vào thẻ.
    khung.appendChild(muc); // Đưa thẻ điểm vào danh sách.
  }); // Kết thúc duyệt danh sách.
} // Kết thúc hàm tạo danh sách.

async function taiDiemMoPhong() { // Tải các điểm mô phỏng từ máy chủ Flask.
  try { // Bắt lỗi kết nối API.
    const phanHoi = await fetch('/api/simulations/jams'); // Gọi API lấy danh sách điểm.
    const duLieu = await phanHoi.json(); // Đọc phản hồi JSON.
    if (!phanHoi.ok || !duLieu.ok) throw new Error('Không thể tải các điểm mô phỏng.'); // Kiểm tra kết quả API.
    cacDiemMoPhong = duLieu.jams || []; // Cập nhật danh sách điểm trong trình duyệt.
    hienThiDanhSachMoPhong(); // Cập nhật danh sách nút thao tác.
    veCacDiemMoPhong(); // Cập nhật vòng tròn trên bản đồ.
  } catch (loi) { hienThiTrangThaiMoPhong('Không tải được dữ liệu mô phỏng. Hãy kiểm tra máy chủ.', true); } // Báo lỗi nếu không tải được dữ liệu.
} // Kết thúc hàm tải điểm.

async function taoDiemMoPhong(viDo, kinhDo) { // Gửi một điểm mô phỏng mới lên máy chủ.
  const payload = { vi_do: viDo, kinh_do: kinhDo, muc_do: document.getElementById('jam-severity').value, ban_kinh_m: Number(document.getElementById('jam-radius').value) }; // Đóng gói tọa độ, mức độ và bán kính.
  try { // Bắt lỗi trong quá trình tạo điểm.
    const phanHoi = await fetch('/api/simulations/jams', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); // Gửi yêu cầu tạo điểm.
    const duLieu = await phanHoi.json(); // Đọc phản hồi từ Flask.
    if (!phanHoi.ok || !duLieu.ok) throw new Error(duLieu.loi || 'Không tạo được điểm mô phỏng.'); // Báo lỗi nếu dữ liệu không hợp lệ.
    cacDiemMoPhong = duLieu.jams; // Cập nhật danh sách điểm vừa nhận.
    hienThiDanhSachMoPhong(); // Hiển thị điểm mới trong danh sách.
    veCacDiemMoPhong(); // Vẽ vùng kẹt xe mới trên bản đồ.
    hienThiTrangThaiMoPhong(`Đã tạo vùng kẹt xe ${tenMucDo(duLieu.jam.muc_do).toLowerCase()} bán kính ${duLieu.jam.ban_kinh_m} m. Đây là dữ liệu mô phỏng.`); // Xác nhận tạo thành công.
    if (latestTrip) await tinhLaiChuyenDi(); // Nếu đã có tuyến thì tính lại để áp dụng tác động mô phỏng ngay.
  } catch (loi) { hienThiTrangThaiMoPhong(loi.message || 'Không tạo được điểm mô phỏng.', true); } // Hiển thị lỗi nếu không tạo được điểm.
} // Kết thúc hàm tạo điểm.

async function capNhatTrangThaiDiem(diem) { // Bật hoặc tắt một điểm mô phỏng đang có.
  try { // Bắt lỗi API.
    const phanHoi = await fetch(`/api/simulations/jams/${diem.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dang_bat: !diem.dang_bat }) }); // Gửi trạng thái ngược lại.
    const duLieu = await phanHoi.json(); // Đọc danh sách đã cập nhật.
    if (!phanHoi.ok || !duLieu.ok) throw new Error(duLieu.loi || 'Không cập nhật được điểm.'); // Kiểm tra lỗi.
    cacDiemMoPhong = duLieu.jams; // Cập nhật danh sách điểm mới.
    hienThiDanhSachMoPhong(); veCacDiemMoPhong(); // Cập nhật danh sách và vùng trên bản đồ.
    hienThiTrangThaiMoPhong('Đã cập nhật trạng thái điểm mô phỏng.'); // Thông báo kết quả.
    if (latestTrip) await tinhLaiChuyenDi(); // Tính lại thời gian nếu đang có tuyến đường.
  } catch (loi) { hienThiTrangThaiMoPhong(loi.message, true); } // Báo lỗi thao tác.
} // Kết thúc hàm bật/tắt.

async function xoaDiemMoPhong(id) { // Xóa một điểm mô phỏng khỏi danh sách.
  try { // Bắt lỗi API.
    const phanHoi = await fetch(`/api/simulations/jams/${id}`, { method: 'DELETE' }); // Gửi yêu cầu xóa theo mã điểm.
    const duLieu = await phanHoi.json(); // Đọc phản hồi JSON.
    if (!phanHoi.ok || !duLieu.ok) throw new Error(duLieu.loi || 'Không xóa được điểm.'); // Kiểm tra phản hồi.
    cacDiemMoPhong = duLieu.jams; // Cập nhật danh sách mới.
    hienThiDanhSachMoPhong(); veCacDiemMoPhong(); // Cập nhật giao diện và bản đồ.
    hienThiTrangThaiMoPhong('Đã xóa điểm mô phỏng.'); // Thông báo kết quả.
    if (latestTrip) await tinhLaiChuyenDi(); // Tính lại chuyến đi sau khi bỏ ảnh hưởng điểm.
  } catch (loi) { hienThiTrangThaiMoPhong(loi.message, true); } // Báo lỗi nếu xóa thất bại.
} // Kết thúc hàm xóa điểm.

async function tinhLaiChuyenDi() { // Tính lại tuyến hiện tại để cập nhật thời gian do mô phỏng.
  document.getElementById('route-form').requestSubmit(); // Tận dụng lại luồng tìm đường hiện có để tránh lặp mã xử lý.
} // Kết thúc hàm tính lại chuyến đi.

document.getElementById('jam-pick-btn').addEventListener('click', () => { // Bật chế độ đặt điểm bằng cách bấm bản đồ.
  dangDatDiemKetXe = !dangDatDiemKetXe; // Đảo trạng thái chọn điểm.
  document.body.classList.toggle('jam-picking', dangDatDiemKetXe); // Hiển thị con trỏ và viền hướng dẫn khi đang chọn.
  document.getElementById('jam-pick-btn').textContent = dangDatDiemKetXe ? 'Đang chọn… bấm vào bản đồ' : '＋ Đặt điểm trên bản đồ'; // Thay nhãn nút theo chế độ.
  hienThiTrangThaiMoPhong(dangDatDiemKetXe ? 'Chế độ đặt điểm đang bật. Hãy bấm vào vị trí muốn mô phỏng kẹt xe.' : 'Đã thoát chế độ đặt điểm.'); // Hướng dẫn thao tác.
}); // Kết thúc sự kiện bật chế độ đặt điểm.

map.on('click', (event) => { // Xử lý bấm trên bản đồ khi chọn điểm mô phỏng.
  if (!dangDatDiemKetXe) return; // Không làm gì nếu chế độ đặt điểm chưa bật.
  dangDatDiemKetXe = false; // Tắt chế độ sau khi đã chọn một vị trí.
  document.body.classList.remove('jam-picking'); // Bỏ giao diện con trỏ chọn điểm.
  document.getElementById('jam-pick-btn').textContent = '＋ Đặt điểm trên bản đồ'; // Khôi phục nhãn nút.
  viTriMoPhongTam = event.latlng; // Ghi nhận tọa độ người dùng vừa bấm.
  taoDiemMoPhong(event.latlng.lat, event.latlng.lng); // Tạo điểm kẹt xe tại tọa độ đã chọn.
}); // Kết thúc sự kiện bấm bản đồ.

document.getElementById('jam-search-btn').addEventListener('click', async () => { // Tìm điểm mô phỏng bằng địa chỉ nhập tay.
  const diaChi = document.getElementById('jam-address').value.trim(); // Đọc địa chỉ muốn mô phỏng.
  if (diaChi.length < 3) { hienThiTrangThaiMoPhong('Nhập địa chỉ từ 3 ký tự trở lên.', true); return; } // Kiểm tra đầu vào tối thiểu.
  hienThiTrangThaiMoPhong('Đang tìm tọa độ địa chỉ…'); // Hiển thị trạng thái đang tìm.
  try { // Bắt lỗi khi gọi dịch vụ địa lý.
    const phanHoi = await fetch('/api/geocode?q=' + encodeURIComponent(diaChi)); // Gọi API gợi ý địa chỉ hiện có.
    const duLieu = await phanHoi.json(); // Đọc danh sách địa điểm tìm được.
    if (!phanHoi.ok || !duLieu.results || !duLieu.results.length) throw new Error('Không tìm được địa chỉ. Hãy thử thêm phường/quận và TP.HCM.'); // Kiểm tra kết quả tìm kiếm.
    const diem = duLieu.results[0]; // Chọn kết quả phù hợp đầu tiên.
    map.setView([diem.vi_do, diem.kinh_do], 15); // Di chuyển bản đồ đến địa điểm được tìm thấy.
    await taoDiemMoPhong(diem.vi_do, diem.kinh_do); // Tạo điểm mô phỏng tại tọa độ địa chỉ.
  } catch (loi) { hienThiTrangThaiMoPhong(loi.message || 'Không tìm được địa chỉ.', true); } // Báo lỗi tìm địa chỉ.
}); // Kết thúc sự kiện tìm địa chỉ.

document.getElementById('jam-reset-btn').addEventListener('click', async () => { // Xóa toàn bộ điểm mô phỏng theo xác nhận người dùng.
  if (!window.confirm('Bạn muốn xóa tất cả các điểm kẹt xe mô phỏng?')) return; // Tránh xóa nhầm.
  try { // Bắt lỗi API.
    const phanHoi = await fetch('/api/simulations/jams/reset', { method: 'POST' }); // Gửi yêu cầu xóa tất cả điểm.
    const duLieu = await phanHoi.json(); // Đọc kết quả xóa.
    if (!phanHoi.ok || !duLieu.ok) throw new Error('Không thể xóa mô phỏng.'); // Kiểm tra kết quả.
    cacDiemMoPhong = []; hienThiDanhSachMoPhong(); veCacDiemMoPhong(); // Xóa toàn bộ vùng mô phỏng khỏi giao diện.
    hienThiTrangThaiMoPhong('Đã xóa tất cả điểm mô phỏng.'); // Báo hoàn tất.
    if (latestTrip) await tinhLaiChuyenDi(); // Tính lại tuyến để bỏ thời gian phạt mô phỏng.
  } catch (loi) { hienThiTrangThaiMoPhong(loi.message, true); } // Báo lỗi nếu xóa thất bại.
}); // Kết thúc sự kiện đặt lại mô phỏng.

// Tải các điểm mô phỏng khi mở trang và thêm lớp vẽ lên bản đồ.
lopDiemMoPhong.addTo(map); // Đăng ký lớp các điểm mô phỏng lên bản đồ Leaflet.
taiDiemMoPhong(); // Khôi phục các điểm đã lưu từ những lần sử dụng trước.


// ================= PHÒNG THÍ NGHIỆM HỌC MÁY CHƯƠNG 1-9 =================
function taoBangHTML(cot, dong) { // Dựng bảng kết quả từ tên cột và các dòng dữ liệu.
  if (!dong || !dong.length) return '<p>Không có kết quả.</p>'; // Báo khi danh sách rỗng.
  return '<table><thead><tr>' + cot.map(x => `<th>${x}</th>`).join('') + '</tr></thead><tbody>' + dong.map(row => '<tr>' + row.map(x => `<td>${x}</td>`).join('') + '</tr>').join('') + '</tbody></table>'; // Ghép bảng HTML.
}

document.getElementById('run-ml-lab').addEventListener('click', async () => { // Chạy thực nghiệm khi người dùng bấm nút.
  const nut = document.getElementById('run-ml-lab'); // Lấy nút chạy thí nghiệm.
  const status = document.getElementById('ml-lab-status'); // Lấy vùng trạng thái.
  nut.disabled = true; nut.textContent = 'Đang huấn luyện và đánh giá…'; status.textContent = 'Đang chạy các mô hình, vui lòng chờ.'; // Báo tiến trình.
  try { // Bắt lỗi API.
    const response = await fetch('/api/ml-lab'); // Gọi API thực nghiệm ở Flask.
    const data = await response.json(); // Đọc kết quả JSON.
    if (!response.ok || !data.ok) throw new Error(data.loi || 'Không chạy được thực nghiệm.'); // Kiểm tra lỗi.
    document.getElementById('ml-lab-dataset').innerHTML = `<strong>Bộ dữ liệu:</strong> ${data.dataset.samples} mẫu tổng hợp • Huấn luyện: ${data.dataset.train} • Kiểm tra: ${data.dataset.test}<br><strong>Đặc trưng:</strong> ${data.dataset.features.join(' · ')}`; // Hiện thông tin dữ liệu.
    document.getElementById('ml-regression-table').innerHTML = taoBangHTML(['Mô hình','Chương','MAE (phút)','RMSE (phút)','R²'], data.regression.map(x => [x.model,x.chapter,x.mae,x.rmse,x.r2])); // Hiện bảng hồi quy.
    document.getElementById('ml-classification-table').innerHTML = taoBangHTML(['Mô hình','Chương','Accuracy','Precision macro','Recall macro','F1 macro'], data.classification.map(x => [x.model,x.chapter,x.accuracy,x.precision,x.recall,x.f1])); // Hiện bảng phân loại.
    const c = data.clustering; document.getElementById('ml-clustering-result').innerHTML = `<strong>${c.algorithm} – ${c.chapter}</strong><p>Số cụm K = ${c.k}; Silhouette = ${c.silhouette}; số mẫu mỗi cụm: ${c.cluster_sizes.join(', ')}.</p>`; // Hiện kết quả K-Means.
    status.textContent = data.note; // Nêu rõ giới hạn của dữ liệu.
  } catch (error) { status.textContent = 'Lỗi: ' + error.message; } // Hiển thị lỗi.
  finally { nut.disabled = false; nut.textContent = 'Chạy lại thực nghiệm →'; } // Khôi phục nút.
});
