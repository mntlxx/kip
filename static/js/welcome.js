document.addEventListener('DOMContentLoaded', () => {
    // Сразу подтягиваем сетевые интерфейсы при загрузке страницы,
    // чтобы Шаг 2 был готов сразу при переходе.
    fetchInterfaces();
});

function goToStep(stepNumber) {
    document.querySelectorAll('.step').forEach(el => {
        el.classList.remove('active');
    });
    
    const target = document.getElementById(`step-${stepNumber}`);
    if (target) {
        target.classList.add('active');
    }

    // На всякий случай обновляем интерфейсы при переходе на шаг 2
    if (stepNumber === 2) {
        fetchInterfaces();
    }
}

async function fetchInterfaces() {
    const select = document.getElementById('iface-select');
    try {
        const res = await fetch('/api/network/interfaces');
        const data = await res.json();
        
        select.innerHTML = '';

        if (!data.interfaces || data.interfaces.length === 0) {
            const opt = document.createElement('option');
            opt.value = '127.0.0.1';
            opt.innerText = 'Localhost (127.0.0.1)';
            select.appendChild(opt);
        } else {
            data.interfaces.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.ip;
                opt.innerText = `${item.name} (${item.ip})`;
                if (item.ip === data.active_ip) opt.selected = true;
                select.appendChild(opt);
            });
        }

        updateQR(select.value);
    } catch (e) {
        console.error("Ошибка при получении интерфейсов:", e);
        select.innerHTML = '<option value="127.0.0.1">Localhost (127.0.0.1)</option>';
        updateQR('127.0.0.1');
    }
}

function onIfaceChange() {
    const select = document.getElementById('iface-select');
    if (select && select.value) {
        updateQR(select.value);
    }
}

function updateQR(ip) {
    if (!ip) return;
    const port = window.location.port || '8008';
    const url = `http://${ip}:${port}`;
    
    const urlText = document.getElementById('qr-url-text');
    if (urlText) urlText.innerText = url;

    const box = document.getElementById('qr-preview');
    if (box) {
        box.innerHTML = '';
        new QRCode(box, { text: url, width: 120, height: 120 });
    }
}

async function saveIp() {
    const select = document.getElementById('iface-select');
    if (!select) return;
    const ip = select.value;

    try {
        await fetch('/api/network/set-active', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ ip: ip })
        });
        const msg = document.getElementById('save-msg');
        if (msg) {
            msg.style.display = 'block';
            setTimeout(() => msg.style.display = 'none', 2000);
        }
    } catch (e) {
        console.error("Ошибка при сохранении IP:", e);
    }
}

function finishSetup() {
    goToStep(4);

    if (typeof confetti === 'function') {
        confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
    }

    const select = document.getElementById('iface-select');
    const ip = (select && select.value) ? select.value : window.location.hostname;
    const port = window.location.port || '8008';
    const url = `http://${ip}:${port}`;

    const box = document.getElementById('final-qr');
    if (box) {
        box.innerHTML = '';
        new QRCode(box, { text: url, width: 160, height: 160 });
    }
}

window.finishAndReload = async function finishAndReload() {
    try {
        await fetch('/api/reload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) {
        console.log("Запрос перезагрузки отправлен...");
    }
    setTimeout(() => {
        window.location.href = '/';
    }, 1500);
}