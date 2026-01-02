document.addEventListener("DOMContentLoaded", function () {
    console.log("Bookly JS loaded");

    if (typeof PDF_URL !== 'undefined') {
        initPDFReader();
    }
});

function initPDFReader() {
    let pdfDoc = null;
    let pageNum = START_PAGE;
    let pageRendering = false;
    let pageNumPending = null;
    const scale = 1.5; // Масштаб сторінки (1.5 = 150%)
    const canvas = document.getElementById('the-canvas');
    const ctx = canvas.getContext('2d');
    const loader = document.getElementById('loader');

    // Елементи інтерфейсу
    const pageNumDisplay = document.getElementById('current-page-num');
    const totalPagesDisplay = document.getElementById('total-pages-num');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const progressFill = document.getElementById('progress-fill');

    // 1. Завантажуємо документ
    pdfjsLib.getDocument(PDF_URL).promise.then(function(pdfDoc_) {
        pdfDoc = pdfDoc_;
        totalPagesDisplay.textContent = pdfDoc.numPages;
        loader.style.display = 'none'; // Ховаємо напис "Завантаження"

        // Якщо збережена сторінка більше ніж є в книзі, скидаємо на останню
        if (pageNum > pdfDoc.numPages) pageNum = pdfDoc.numPages;

        renderPage(pageNum);
    }).catch(function(error) {
        console.error('Error loading PDF:', error);
        loader.textContent = 'Помилка завантаження файлу';
    });

    // 2. Функція малювання сторінки
    function renderPage(num) {
        pageRendering = true;

        // Отримуємо сторінку
        pdfDoc.getPage(num).then(function(page) {
            const viewport = page.getViewport({scale: scale});

            // Встановлюємо розміри canvas під розмір сторінки
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            // Рендеримо
            const renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };
            const renderTask = page.render(renderContext);

            // Чекаємо завершення рендеру
            renderTask.promise.then(function() {
                pageRendering = false;
                if (pageNumPending !== null) {
                    // Якщо поки ми малювали, користувач вже клікнув далі
                    renderPage(pageNumPending);
                    pageNumPending = null;
                }
            });
        });

        // Оновлюємо інтерфейс
        pageNumDisplay.textContent = num;
        updateButtons();
        updateProgressBar();
        saveProgress(num);
    }

    // Якщо ми хочемо перемкнути сторінку, поки попередня ще малюється
    function queueRenderPage(num) {
        if (pageRendering) {
            pageNumPending = num;
        } else {
            renderPage(num);
        }
    }

    // 3. Обробники кнопок
    function onPrevPage() {
        if (pageNum <= 1) return;
        pageNum--;
        queueRenderPage(pageNum);
    }

    function onNextPage() {
        if (pageNum >= pdfDoc.numPages) return;
        pageNum++;
        queueRenderPage(pageNum);
    }

    prevBtn.addEventListener('click', onPrevPage);
    nextBtn.addEventListener('click', onNextPage);

    // Додаємо керування стрілками клавіатури
    document.addEventListener('keydown', (e) => {
        if (e.key === "ArrowRight") onNextPage();
        if (e.key === "ArrowLeft") onPrevPage();
    });

    // 4. Допоміжні функції
    function updateButtons() {
        prevBtn.disabled = pageNum <= 1;
        if (!pdfDoc) return;
        nextBtn.disabled = pageNum >= pdfDoc.numPages;
    }

    function updateProgressBar() {
        if (!pdfDoc) return;
        const percent = (pageNum / pdfDoc.numPages) * 100;
        progressFill.style.width = percent + "%";
    }

    function saveProgress(currentPage) {
        const url = `/progress/update/${RENTAL_ID}/`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({
                current_page: currentPage
            })
        }).catch(err => console.error('Error saving progress:', err));
    }
}