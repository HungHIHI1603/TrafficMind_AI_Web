# -*- coding: utf-8 -*-
"""Phòng thí nghiệm mô hình theo phạm vi Học máy và ứng dụng, Chương 1-9.

DỮ LIỆU: dữ liệu tổng hợp phục vụ thực nghiệm học thuật, KHÔNG phải cảm biến
hoặc dữ liệu ùn tắc trực tiếp. Thay bằng dữ liệu thật có nguồn rõ ràng khi có.
"""
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPRegressor
from sklearn.cluster import KMeans
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, silhouette_score)


def tao_bo_du_lieu(so_mau=2400, seed=42):
    """Tạo dữ liệu mô phỏng có đặc trưng và nhãn rõ ràng để chạy được demo."""
    rng = np.random.default_rng(seed)
    km = rng.uniform(1, 40, so_mau)
    gio = rng.integers(0, 24, so_mau)
    mua = rng.integers(0, 2, so_mau)  # 0: giả định khô ráo, 1: giả định mưa
    loai_duong = rng.integers(0, 3, so_mau)  # 0: nhỏ, 1: vừa, 2: lớn
    gio_cao_diem = (((gio >= 7) & (gio <= 9)) | ((gio >= 16) & (gio <= 19))).astype(int)
    he_so_gio = 1.0 + 0.42 * gio_cao_diem + 0.22 * mua + 0.08 * (loai_duong == 0)
    toc_do_co_so = np.choose(loai_duong, [24.0, 38.0, 52.0])
    phut_co_so = km / toc_do_co_so * 60
    muc_tac = np.clip(0.15 + 0.58 * gio_cao_diem + 0.20 * mua + 0.10 * (loai_duong == 0) + rng.normal(0, 0.12, so_mau), 0, 1)
    thoi_gian = np.maximum(1, phut_co_so * (1 + muc_tac) + rng.normal(0, 2.0, so_mau))
    # Nhãn phân loại ba mức được tạo theo mức tắc nghẽn mô phỏng.
    nhan_muc_do = np.where(muc_tac < 0.38, 0, np.where(muc_tac < 0.68, 1, 2))
    X = np.column_stack([km, gio, mua, loai_duong, gio_cao_diem, muc_tac])
    return X, thoi_gian, nhan_muc_do


def chay_thuc_nghiem():
    """So sánh mô hình thuộc các chương 1-9 bằng cùng cách chia dữ liệu."""
    X, y_time, y_class = tao_bo_du_lieu()
    X_train, X_test, yt_train, yt_test, yc_train, yc_test = train_test_split(
        X, y_time, y_class, test_size=0.2, random_state=42, stratify=y_class)

    # Chương 1, 5 và 9: hồi quy dự đoán thời gian (đầu ra liên tục).
    regressors = [
        ("Linear Regression", "Chương 1", LinearRegression()),
        ("Random Forest Regressor", "Chương 5", RandomForestRegressor(n_estimators=120, max_depth=12, random_state=42, n_jobs=-1)),
        ("MLP Regressor", "Chương 9", make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32), activation="relu", solver="adam", max_iter=450, early_stopping=True, random_state=42)))
    ]
    regression_results = []
    for name, chapter, model in regressors:
        model.fit(X_train, yt_train)
        pred = model.predict(X_test)
        regression_results.append({
            "model": name, "chapter": chapter,
            "mae": round(float(mean_absolute_error(yt_test, pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(yt_test, pred))), 3),
            "r2": round(float(r2_score(yt_test, pred)), 4)
        })

    # Chương 2-6: phân loại mức ùn tắc (nhẹ/vừa/cao).
    X_class = X[:, :5]  # Không đưa biến mức tắc nghẽn dùng để sinh nhãn vào đầu vào, tránh rò rỉ nhãn.
    Xc_train, Xc_test, ycc_train, ycc_test = train_test_split(
        X_class, y_class, test_size=0.2, random_state=42, stratify=y_class)
    classifiers = [
        ("Logistic Regression", "Chương 2", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))),
        ("Naive Bayes", "Chương 3", GaussianNB()),
        ("KNN", "Chương 4", make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=7))),
        ("Decision Tree", "Chương 5", DecisionTreeClassifier(max_depth=8, random_state=42)),
        ("Random Forest Classifier", "Chương 5", RandomForestClassifier(n_estimators=120, max_depth=10, random_state=42, n_jobs=-1)),
        ("SVM", "Chương 6", make_pipeline(StandardScaler(), SVC(C=1.0, kernel="rbf")))
    ]
    classification_results = []
    for name, chapter, model in classifiers:
        model.fit(Xc_train, ycc_train)
        pred = model.predict(Xc_test)
        classification_results.append({
            "model": name, "chapter": chapter,
            "accuracy": round(float(accuracy_score(ycc_test, pred)), 4),
            "precision": round(float(precision_score(ycc_test, pred, average="macro", zero_division=0)), 4),
            "recall": round(float(recall_score(ycc_test, pred, average="macro", zero_division=0)), 4),
            "f1": round(float(f1_score(ycc_test, pred, average="macro", zero_division=0)), 4),
            "confusion_matrix": confusion_matrix(ycc_test, pred, labels=[0, 1, 2]).tolist()
        })

    # Chương 8: K-Means không dùng nhãn mức độ trong lúc phân cụm.
    X_cluster = StandardScaler().fit_transform(X[:, [0, 1, 4, 5]])
    kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)
    cluster_ids = kmeans.fit_predict(X_cluster)
    sil = silhouette_score(X_cluster, cluster_ids)
    counts = np.bincount(cluster_ids, minlength=3).tolist()

    return {
        "ok": True,
        "dataset": {"samples": int(len(X)), "train": int(len(X_train)), "test": int(len(X_test)), "features": ["Quãng đường (km)", "Giờ trong ngày", "Mưa (giả lập)", "Loại đường", "Giờ cao điểm", "Mức tắc nghẽn mô phỏng (chỉ dùng cho hồi quy/phân cụm)"], "classification_features": ["Quãng đường (km)", "Giờ trong ngày", "Mưa (giả lập)", "Loại đường", "Giờ cao điểm"]},
        "regression": regression_results,
        "classification": classification_results,
        "clustering": {"algorithm": "K-Means", "chapter": "Chương 8", "k": 3, "silhouette": round(float(sil), 4), "cluster_sizes": counts},
        "note": "Toàn bộ kết quả trên dữ liệu tổng hợp tạo bằng quy tắc mô phỏng; không phải bằng chứng độ chính xác giao thông ngoài thực tế. Chương 7 là nhóm độ đo đánh giá, không phải một mô hình dự đoán riêng."
    }
