/**
 * Main JavaScript File
 * لعبة المافيا أونلاين
 */

// ==================== Global Variables ====================

let socket = null;

// ==================== Initialize Socket.IO ====================

document.addEventListener('DOMContentLoaded', function() {
    // تهيئة Socket.IO إذا لم يتم تهيئتها
    if (typeof io !== 'undefined') {
        socket = io();
        setupSocketListeners();
    }
});

// ==================== Socket.IO Listeners ====================

function setupSocketListeners() {
    if (!socket) return;

    socket.on('connect', function() {
        console.log('✅ متصل بالخادم');
        document.body.classList.remove('disconnected');
    });

    socket.on('disconnect', function() {
        console.log('❌ قطع الاتصال بالخادم');
        document.body.classList.add('disconnected');
    });

    socket.on('error', function(error) {
        console.error('❌ خطأ في الاتصال:', error);
        showNotification(error.message || 'حدث خطأ في الاتصال', 'error');
    });
}

// ==================== Utility Functions ====================

/**
 * عرض إخطار للمستخدم
 * @param {string} message - الرسالة
 * @param {string} type - نوع الإخطار (success, error, warning, info)
 * @param {number} duration - مدة الإخطار بالميلي ثانية
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // إضافة الحركة
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, duration);
    }
    
    return notification;
}

/**
 * إرسال طلب AJAX
 * @param {string} url - رابط الطلب
 * @param {string} method - الطريقة (GET, POST, etc)
 * @param {object} data - البيانات المرسلة
 */
async function fetchData(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const json = await response.json();
        
        if (!response.ok) {
            throw new Error(json.error || 'حدث خطأ ما');
        }
        
        return json;
    } catch (error) {
        console.error('Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

/**
 * نسخ نص إلى الحافظة
 * @param {string} text - النص المراد نسخه
 */
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text);
}

/**
 * تأخير لعدد معين من الميلي ثانية
 * @param {number} ms - عدد الميلي ثانية
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * التحقق من صحة اسم اللاعب
 * @param {string} username - اسم اللاعب
 */
function validateUsername(username) {
    if (!username || typeof username !== 'string') {
        return { valid: false, error: 'الاسم غير صحيح' };
    }

    username = username.trim();

    if (username.length < 2) {
        return { valid: false, error: 'الاسم يجب أن يكون على الأقل حرفين' };
    }

    if (username.length > 50) {
        return { valid: false, error: 'الاسم طويل جداً' };
    }

    // التحقق من أنه لا يحتوي على أحرف خاصة خطرة
    if (!/^[\w\u0600-\u06FF\s\-]+$/u.test(username)) {
        return { valid: false, error: 'الاسم يحتوي على أحرف غير مسموحة' };
    }

    return { valid: true };
}

/**
 * التحقق من صحة رمز الغرفة
 * @param {string} code - رمز الغرفة
 */
function validateRoomCode(code) {
    if (!code || typeof code !== 'string') {
        return { valid: false, error: 'الرمز غير صحيح' };
    }

    code = code.trim().toUpperCase();

    if (code.length !== 6) {
        return { valid: false, error: 'الرمز يجب أن يكون 6 أحرف' };
    }

    if (!/^[A-Z0-9]+$/.test(code)) {
        return { valid: false, error: 'الرمز يجب أن يحتوي على أحرف وأرقام فقط' };
    }

    return { valid: true, code: code };
}

/**
 * تنسيق الوقت
 * @param {string|Date} date - التاريخ
 */
function formatTime(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }

    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) {
        return 'الآن للتو';
    } else if (minutes < 60) {
        return `قبل ${minutes} دقيقة`;
    } else if (hours < 24) {
        return `قبل ${hours} ساعة`;
    } else if (days < 7) {
        return `قبل ${days} يوم`;
    } else {
        return date.toLocaleDateString('ar-SA');
    }
}

// ==================== DOM Utilities ====================

/**
 * إنشاء عنصر DOM من HTML string
 * @param {string} html - HTML string
 */
function createElementFromHTML(html) {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.firstElementChild;
}

/**
 * إضافة/إزالة class من عنصر
 * @param {HTMLElement} element - العنصر
 * @param {string} className - اسم الكلاس
 * @param {boolean} add - إضافة أم إزالة
 */
function toggleClass(element, className, add = null) {
    if (add === null) {
        element.classList.toggle(className);
    } else if (add) {
        element.classList.add(className);
    } else {
        element.classList.remove(className);
    }
}

/* ==================== Notification Styles ==================== */

const notificationStyles = `
<style>
    .notification {
        position: fixed;
        bottom: -100px;
        left: 20px;
        right: auto;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        font-weight: 600;
        animation: slideUpNotification 0.3s ease-out forwards;
        max-width: 400px;
    }

    .notification.show {
        animation: slideDownNotification 0.3s ease-out forwards;
    }

    .notification-success {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }

    .notification-error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    .notification-warning {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }

    .notification-info {
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }

    @keyframes slideUpNotification {
        from {
            bottom: -100px;
            opacity: 0;
        }
        to {
            bottom: 20px;
            opacity: 1;
        }
    }

    @keyframes slideDownNotification {
        from {
            bottom: 20px;
            opacity: 1;
        }
        to {
            bottom: -100px;
            opacity: 0;
        }
    }

    @media (max-width: 768px) {
        .notification {
            left: 10px;
            right: 10px;
            max-width: none;
        }
    }
</style>
`;

// إضافة الأنماط عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('div');
    style.innerHTML = notificationStyles;
    document.head.appendChild(style.querySelector('style'));
});

// ==================== Export Functions ====================

// تصدير الدوال للاستخدام في الصفحات الأخرى
window.mafia = {
    showNotification,
    fetchData,
    copyToClipboard,
    delay,
    validateUsername,
    validateRoomCode,
    formatTime,
    createElementFromHTML,
    toggleClass
};
