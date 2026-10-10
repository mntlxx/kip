document.addEventListener('DOMContentLoaded', () => {
    initCodeCopyButtons();
});

function initCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('.guide-code-block');
    codeBlocks.forEach(block => {
        const btn = document.createElement('button');
        btn.innerText = '[копировать]';
        btn.className = 'btn-copy';
        
        btn.addEventListener('click', () => {
            const codeText = block.querySelector('code').innerText;
            
            // Проверяем доступность современного API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(codeText).then(() => {
                    showCopiedFeedback(btn);
                }).catch(err => {
                    console.warn('Clipboard API error, falling back:', err);
                    fallbackCopyText(codeText, btn);
                });
            } else {
                // Запасной вариант для HTTP / локальной сети по IP
                fallbackCopyText(codeText, btn);
            }
        });
        
        block.appendChild(btn);
    });
}

function fallbackCopyText(text, btn) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    // Скрываем textarea от глаз, но оставляем в DOM
    textarea.style.position = 'fixed';
    textarea.style.top = '0';
    textarea.style.left = '0';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopiedFeedback(btn);
        } else {
            console.error('Не удалось скопировать текст');
        }
    } catch (err) {
        console.error('Ошибка при копировании:', err);
    }

    document.body.removeChild(textarea);
}

function showCopiedFeedback(btn) {
    btn.innerText = '[скопировано!]';
    btn.style.color = '#4ade80';
    setTimeout(() => {
        btn.innerText = '[копировать]';
        btn.style.color = '';
    }, 2000);
}