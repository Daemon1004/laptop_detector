from flask import Flask, render_template, request, jsonify, send_file
import cv2
import json
import io
import time
import os
from datetime import datetime
from ultralytics import YOLO
from openpyxl import Workbook

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

model = YOLO('yolov8n.pt')
HISTORY_FILE = 'history.json'


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def detect_laptops(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, 0, []

    results = model(img, conf=0.5, imgsz=1280)  # ВАЖНО: imgsz=1280 ловит мелкие и дальние ноутбуки

    laptop_count = 0
    detections = []
    for result in results:
        for box in result.boxes:
            if int(box.cls) == 63:  # ВАЖНО: 63 - класс "laptop" в наборе COCO
                laptop_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, f'Laptop {conf:.2f}', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                detections.append({'coordinates': [x1, y1, x2, y2], 'confidence': conf})

    return img, laptop_count, detections


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = datetime.now().strftime('%Y%m%d_%H%M%S_') + file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        start_time = time.time()
        processed_img, laptop_count, detections = detect_laptops(file_path)
        process_time_ms = int((time.time() - start_time) * 1000)

        if processed_img is None:
            return jsonify({'error': 'Invalid image file'}), 400

        result_filename = f'result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        cv2.imwrite(result_path, processed_img)

        history = load_history()
        history.append({
            'timestamp': datetime.now().isoformat(),
            'original_file': filename,
            'result_file': result_filename,
            'laptop_count': laptop_count,
            'process_time_ms': process_time_ms,
            'detections': detections
        })
        save_history(history)

        return jsonify({
            'success': True,
            'laptop_count': laptop_count,
            'process_time_ms': process_time_ms,
            'result_image': f'/static/results/{result_filename}',
            'detections': detections
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def get_history():
    try:
        return jsonify({'history': load_history()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/clear-history', methods=['POST'])
def clear_history():
    try:
        save_history([])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/export', methods=['GET'])
def export_history():
    try:
        history = load_history()
        wb = Workbook()
        ws = wb.active
        ws.title = 'История'
        ws.append(['Дата и время', 'Файл', 'Найдено ноутбуков', 'Время обработки, мс'])
        for item in history:
            ws.append([
                item.get('timestamp', ''),
                item.get('original_file', ''),
                item.get('laptop_count', 0),
                item.get('process_time_ms', '')
            ])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='laptop_detection_report.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'model': 'YOLOv8n'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
