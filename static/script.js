document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('imageInput');
    const fileNameSpan = document.getElementById('fileName');
    const processBtn = document.getElementById('processBtn');
    const loading = document.getElementById('loading');
    const resultsSection = document.getElementById('resultsSection');
    const errorBox = document.getElementById('errorBox');
    const originalImage = document.getElementById('originalImage');
    const resultImage = document.getElementById('resultImage');
    const laptopCount = document.getElementById('laptopCount');
    const processTime = document.getElementById('processTime');
    const detectionsList = document.getElementById('detectionsList');
    const showHistoryBtn = document.getElementById('showHistoryBtn');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const historyList = document.getElementById('historyList');

    let selectedFile = null;

    imageInput.addEventListener('change', function(e) {
        selectedFile = e.target.files[0];
        if (selectedFile) {
            fileNameSpan.textContent = 'Выбран: ' + selectedFile.name;
            processBtn.disabled = false;
        } else {
            fileNameSpan.textContent = '';
            processBtn.disabled = true;
        }
    });

    processBtn.addEventListener('click', async function() {
        if (!selectedFile) {
            showError('Пожалуйста, выберите изображение');
            return;
        }

        const reader = new FileReader();
        reader.onload = async function(e) {
            originalImage.src = e.target.result;

            const formData = new FormData();
            formData.append('image', selectedFile);

            loading.style.display = 'block';
            resultsSection.classList.remove('active');
            hideError();

            const startTime = performance.now();

            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                const endTime = performance.now();

                loading.style.display = 'none';

                if (data.success) {
                    resultImage.src = data.result_image + '?t=' + Date.now();
                    laptopCount.textContent = data.laptop_count;
                    processTime.textContent = Math.round(endTime - startTime);

                    if (data.detections && data.detections.length > 0) {
                        detectionsList.innerHTML = '';
                        data.detections.forEach((det, index) => {
                            const item = document.createElement('div');
                            item.className = 'detection-item';
                            item.innerHTML = `
                                <strong>Объект ${index + 1}</strong><br>
                                Координаты: (${det.coordinates[0]}, ${det.coordinates[1]}) - (${det.coordinates[2]}, ${det.coordinates[3]})<br>
                                Уверенность: ${(det.confidence * 100).toFixed(1)}%
                            `;
                            detectionsList.appendChild(item);
                        });
                    } else {
                        detectionsList.innerHTML = '<div class="detection-item">Ноутбуки не обнаружены</div>';
                    }

                    resultsSection.classList.add('active');
                } else {
                    showError('Ошибка при обработке: ' + (data.error || 'неизвестная ошибка'));
                }
            } catch (error) {
                loading.style.display = 'none';
                showError('Ошибка подключения: ' + error.message);
                console.error('Error:', error);
            }
        };
        reader.readAsDataURL(selectedFile);
    });

    showHistoryBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/history');
            const data = await response.json();

            if (data.history && data.history.length > 0) {
                historyList.innerHTML = '';
                data.history.forEach((item, index) => {
                    const date = new Date(item.timestamp);
                    const historyItem = document.createElement('div');
                    historyItem.className = 'history-item';
                    historyItem.innerHTML = `
                        <div class="history-time">${date.toLocaleString('ru-RU')}</div>
                        <div class="history-count">Ноутбуков найдено: <strong>${item.laptop_count}</strong></div>
                        <div style="font-size: 12px; margin-top: 5px; color: #666;">
                            Файл: ${item.original_file}
                        </div>
                    `;
                    historyList.appendChild(historyItem);
                });
                historyList.style.display = 'block';
            } else {
                historyList.innerHTML = '<div class="history-item">История пуста</div>';
                historyList.style.display = 'block';
            }
        } catch (error) {
            showError('Ошибка загрузки истории: ' + error.message);
        }
    });

    clearHistoryBtn.addEventListener('click', async function() {
        if (confirm('Вы уверены? Это действие нельзя отменить.')) {
            try {
                const response = await fetch('/clear-history', {
                    method: 'POST'
                });
                const data = await response.json();

                if (data.success) {
                    historyList.innerHTML = '<div class="history-item">История очищена</div>';
                    historyList.style.display = 'block';
                } else {
                    showError('Ошибка при очистке истории');
                }
            } catch (error) {
                showError('Ошибка: ' + error.message);
            }
        }
    });

    function showError(message) {
        errorBox.textContent = message;
        errorBox.classList.add('active');
    }

    function hideError() {
        errorBox.classList.remove('active');
    }
});
