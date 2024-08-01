import os
import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

# 대사 추출 함수
def extract_dialogues_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    dialogues = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")

        for line in text.split('\n'):
            if '로' in line:  # 대사 필터링 조건
                dialogues.append(line)

    return dialogues

# 웹 애플리케이션 라우트
@app.route('/')
def upload_file():
    return render_template('upload.html')

@app.route('/uploader', methods=['POST'])
def uploader():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    if file and file.filename.endswith('.pdf'):
        file_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)
        
        dialogues = extract_dialogues_from_pdf(file_path)
        
        output_txt_path = file_path.replace('.pdf', '_dialogues.txt')
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            for dialogue in dialogues:
                f.write(dialogue + '\n')
        
        return send_file(output_txt_path, as_attachment=True)
    
    return 'Invalid file format. Please upload a PDF file.'

if __name__ == '__main__':
    app.run(debug=True)