import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
from flask import Flask, request, render_template

# Tesseract 경로 설정 (Windows의 경우)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

def preprocess_image(image):
    # 이미지를 numpy 배열로 변환
    img_array = np.array(image)

    # BGR에서 그레이스케일로 변환
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # 가우시안 블러 적용
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive Thresholding 적용
    adaptive_thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    return adaptive_thresh

def detect_speech_bubbles(binary_image):
    # 윤곽선 찾기
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 말풍선으로 추정되는 윤곽선 필터링
    speech_bubbles = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:  # 최소 크기 기준 조정
            x, y, w, h = cv2.boundingRect(contour)
            # 말풍선의 비율을 고려한 필터링
            aspect_ratio = float(w) / h
            if 0.5 < aspect_ratio < 2.5:
                speech_bubbles.append((x, y, w, h))

    return speech_bubbles

def extract_text_from_bubble(image, bubble):
    x, y, w, h = bubble
    roi = image[y:y + h, x:x + w]

    # ROI 전처리
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, binary_roi = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Tesseract OCR 설정
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(binary_roi, lang='kor', config=custom_config)

    return clean_text(text)

def clean_text(text):
    # 텍스트 정제
    text = re.sub(r'[^\w\s가-힣]', ' ', text)  # 한글, 영어, 숫자, 공백 외의 문자 제거
    text = re.sub(r'\s+', ' ', text)  # 연속된 공백을 하나의 공백으로 축소
    return text.strip()

def extract_text_from_image(image_path):
    # 이미지 파일 열기
    image = cv2.imread(image_path)

    # 이미지 전처리
    preprocessed_image = preprocess_image(image)

    # 말풍선 감지
    speech_bubbles = detect_speech_bubbles(preprocessed_image)

    # 각 말풍선에서 텍스트 추출
    extracted_texts = []
    for bubble in speech_bubbles:
        text = extract_text_from_bubble(image, bubble)
        if text:
            extracted_texts.append(text)

    return "\n".join(extracted_texts)

def extract_text_from_image_data(image_bytes):
    # 이미지를 numpy 배열로 변환
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 이미지 전처리
    preprocessed_image = preprocess_image(image)

    # 말풍선 감지
    speech_bubbles = detect_speech_bubbles(preprocessed_image)

    # 각 말풍선에서 텍스트 추출
    extracted_texts = []
    for bubble in speech_bubbles:
        text = extract_text_from_bubble(image, bubble)
        if text:
            extracted_texts.append(text)

    return "\n".join(extracted_texts)

def extract_text_from_images_in_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texts = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # 이미지에서 텍스트 추출
            text = extract_text_from_image_data(image_bytes)
            if text:
                texts.append(text)

    return texts

@app.route('/')
def upload_file():
    return render_template('upload.html')

@app.route('/uploader', methods=['POST'])
def uploader():
    if 'file' not in request.files:
        return render_template('upload.html', text='파일이 선택되지 않았습니다.')

    file = request.files['file']

    if file.filename == '':
        return render_template('upload.html', text='파일이 선택되지 않았습니다.')

    if file:
        file_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)

        if file.filename.lower().endswith('.pdf'):
            texts = extract_text_from_images_in_pdf(file_path)
        elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            texts = [extract_text_from_image(file_path)]
        else:
            return render_template('upload.html', text='잘못된 파일 형식입니다. PDF 또는 이미지 파일을 업로드하세요.')

        text_content = "\n\n".join(texts)

        return render_template('upload.html', text=text_content)

    return render_template('upload.html', text='파일을 처리하는 중 오류가 발생했습니다.')

if __name__ == '__main__':
    app.run(debug=True)
