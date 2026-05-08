"""
Create 5 extended STEM sample PDFs for benchmarking.
Each PDF + corresponding ground-truth JSON in tests/sample_data/.

Topics:
1. Vi tích phân (calculus)
2. Đại số tuyến tính (linear algebra) — matrix
3. Hoá học (chemistry equation)
4. Thống kê (statistics with chart)
5. Vật lý nâng cao (physics — wave equation)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

import fitz

OUT_DIR = Path("tests/sample_data")
GT_DIR = OUT_DIR / "benchmarks"
OUT_DIR.mkdir(parents=True, exist_ok=True)
GT_DIR.mkdir(parents=True, exist_ok=True)


def make_page(doc, title, lines, formulas, chart_caption=None):
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(60, 60), title, fontsize=20, color=(0, 0, 0.6))
    y = 100
    for line in lines:
        page.insert_text(fitz.Point(60, y), line, fontsize=12)
        y += 22
    y += 10
    for formula in formulas:
        page.insert_text(fitz.Point(120, y), formula, fontsize=18, color=(0.8, 0, 0))
        y += 35
    if chart_caption:
        rect = fitz.Rect(80, y, 515, y + 180)
        page.draw_rect(rect, color=(0, 0, 0), width=1)
        page.insert_text(fitz.Point(rect.x0 + 20, rect.y1 + 20), chart_caption, fontsize=10)
        # Simple line chart
        for i in range(5):
            x_pt = rect.x0 + 30 + i * 80
            y_pt = rect.y1 - 30 - i * 25
            page.draw_circle(fitz.Point(x_pt, y_pt), 3, color=(0, 0, 1), fill=(0, 0, 1))
            if i > 0:
                page.draw_line(prev, fitz.Point(x_pt, y_pt), color=(1, 0, 0), width=2)
            prev = fitz.Point(x_pt, y_pt)


# Sample 1: Calculus
doc1 = fitz.open()
make_page(doc1,
    "Vi tich phan - Tich phan xac dinh",
    [
        "Cho ham so f(x) = x^2 + 2x lien tuc tren doan [0, 3].",
        "Tich phan xac dinh tu 0 den 3 cua f(x) duoc tinh boi cong thuc Newton-Leibniz.",
    ],
    [
        "integral_0^3 (x^2 + 2x) dx = [x^3/3 + x^2]_0^3 = 18",
        "F(b) - F(a) = F(3) - F(0)",
    ],
)
doc1.save(str(OUT_DIR / "sample_calculus.pdf"))
doc1.close()

# Sample 2: Linear algebra - Matrix
doc2 = fitz.open()
make_page(doc2,
    "Dai so tuyen tinh - Phep nhan ma tran",
    [
        "Cho hai ma tran A va B. Tich AB la ma tran C voi:",
        "C[i][j] = sum_k A[i][k] * B[k][j]",
    ],
    [
        "A = [[1, 2], [3, 4]]",
        "B = [[5, 6], [7, 8]]",
        "AB = [[19, 22], [43, 50]]",
    ],
)
doc2.save(str(OUT_DIR / "sample_linear_algebra.pdf"))
doc2.close()

# Sample 3: Chemistry
doc3 = fitz.open()
make_page(doc3,
    "Hoa hoc - Phan ung dot chay metan",
    [
        "Phan ung chay hoan toan cua metan trong oxi tao thanh CO2 va nuoc.",
        "Day la phan ung toa nhiet voi delta H = -890 kJ/mol.",
    ],
    [
        "CH_4 + 2O_2 -> CO_2 + 2H_2O",
        "Delta H = -890 kJ/mol",
    ],
)
doc3.save(str(OUT_DIR / "sample_chemistry.pdf"))
doc3.close()

# Sample 4: Statistics with chart
doc4 = fitz.open()
make_page(doc4,
    "Thong ke - Phan phoi chuan",
    [
        "Phan phoi chuan voi trung binh muy va do lech chuan sigma.",
        "Ham mat do xac suat duoc cho boi:",
    ],
    [
        "f(x) = 1/(sigma*sqrt(2*pi)) * exp(-(x-muy)^2/(2*sigma^2))",
    ],
    chart_caption="Bieu do duong cong phan phoi chuan: Truc X = gia tri, Truc Y = mat do xac suat",
)
doc4.save(str(OUT_DIR / "sample_statistics.pdf"))
doc4.close()

# Sample 5: Wave physics
doc5 = fitz.open()
make_page(doc5,
    "Vat ly - Phuong trinh song",
    [
        "Phuong trinh song mot chieu mo ta dao dong truyen di trong moi truong dan hoi.",
        "Buoc song lambda lien quan voi tan so f va van toc v boi v = lambda * f.",
    ],
    [
        "y(x, t) = A * sin(k*x - omega*t + phi)",
        "v = lambda * f = omega / k",
    ],
)
doc5.save(str(OUT_DIR / "sample_wave_physics.pdf"))
doc5.close()

# Ground truth JSON for each
gts = {
    "sample_calculus_gt.json": [
        {"id": "gt_001", "type": "text", "spoken_text": "Cho hàm số f của x bằng x bình phương cộng 2 x, liên tục trên đoạn không tới ba."},
        {"id": "gt_002", "type": "text", "spoken_text": "Tích phân xác định từ 0 đến 3 của f của x được tính bởi công thức Newton-Leibniz."},
        {"id": "gt_003", "type": "math", "spoken_text": "Tích phân từ 0 đến 3 của x bình phương cộng 2 x dx bằng x mũ 3 chia 3 cộng x bình phương đánh giá tại 3 trừ 0 bằng 18."},
        {"id": "gt_004", "type": "math", "spoken_text": "F của b trừ F của a bằng F của 3 trừ F của 0."},
    ],
    "sample_linear_algebra_gt.json": [
        {"id": "gt_001", "type": "text", "spoken_text": "Cho hai ma trận A và B. Tích A B là ma trận C với."},
        {"id": "gt_002", "type": "math", "spoken_text": "C i j bằng tổng theo k của A i k nhân B k j."},
        {"id": "gt_003", "type": "math", "spoken_text": "Ma trận A bằng ma trận hàng một là một và hai, hàng hai là ba và bốn."},
        {"id": "gt_004", "type": "math", "spoken_text": "Ma trận B bằng ma trận hàng một là năm và sáu, hàng hai là bảy và tám."},
        {"id": "gt_005", "type": "math", "spoken_text": "Tích A B bằng ma trận hàng một là 19 và 22, hàng hai là 43 và 50."},
    ],
    "sample_chemistry_gt.json": [
        {"id": "gt_001", "type": "text", "spoken_text": "Phản ứng cháy hoàn toàn của metan trong oxy tạo thành C O 2 và nước."},
        {"id": "gt_002", "type": "text", "spoken_text": "Đây là phản ứng tỏa nhiệt với delta H bằng âm 890 kilô jun trên mol."},
        {"id": "gt_003", "type": "math", "spoken_text": "C H 4 cộng 2 O 2 tạo thành C O 2 cộng 2 H 2 O."},
        {"id": "gt_004", "type": "math", "spoken_text": "Delta H bằng âm 890 kilô jun trên mol."},
    ],
    "sample_statistics_gt.json": [
        {"id": "gt_001", "type": "text", "spoken_text": "Phân phối chuẩn với trung bình muy và độ lệch chuẩn sigma."},
        {"id": "gt_002", "type": "text", "spoken_text": "Hàm mật độ xác suất được cho bởi:"},
        {"id": "gt_003", "type": "math", "spoken_text": "f của x bằng 1 chia sigma nhân căn 2 pi nhân e mũ trừ x trừ muy bình phương chia 2 sigma bình phương."},
        {"id": "gt_004", "type": "chart", "spoken_text": "Biểu đồ đường cong phân phối chuẩn với trục hoành là giá trị và trục tung là mật độ xác suất."},
    ],
    "sample_wave_physics_gt.json": [
        {"id": "gt_001", "type": "text", "spoken_text": "Phương trình sóng một chiều mô tả dao động truyền đi trong môi trường đàn hồi."},
        {"id": "gt_002", "type": "text", "spoken_text": "Bước sóng lambda liên quan với tần số f và vận tốc v bởi v bằng lambda nhân f."},
        {"id": "gt_003", "type": "math", "spoken_text": "y của x t bằng A nhân sin của k x trừ omega t cộng phi."},
        {"id": "gt_004", "type": "math", "spoken_text": "Vận tốc bằng lambda nhân f bằng omega chia k."},
    ],
}

for fname, blocks in gts.items():
    (GT_DIR / fname).write_text(
        json.dumps(blocks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

print(f"Created 5 sample PDFs in {OUT_DIR}/")
print(f"Created 5 ground-truth JSONs in {GT_DIR}/")
for f in sorted(OUT_DIR.glob("sample_*.pdf")):
    print(f"  - {f.name}")
for f in sorted(GT_DIR.glob("sample_*_gt.json")):
    print(f"  - {f.name}")
