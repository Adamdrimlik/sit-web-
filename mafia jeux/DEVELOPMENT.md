# ملف تعليمات التطوير

## إعداد بيئة التطوير

### 1. استنساخ المستودع

```bash
git clone <repository-url>
cd mafia-game
```

### 2. إنشاء بيئة افتراضية

```bash
python -m venv venv

# على Windows
venv\Scripts\activate

# على macOS/Linux
source venv/bin/activate
```

### 3. تثبيت المكتبات

```bash
# تثبيت المكتبات الأساسية
pip install -r requirements.txt

# تثبيت مكتبات التطوير (اختياري)
pip install -r requirements-dev.txt
```

### 4. تهيئة قاعدة البيانات

```bash
flask --app app init-db
```

### 5. تشغيل الخادم

```bash
python app.py
```

الخادم سيعمل على `http://localhost:5000`

## هيكل الكود

### app.py
الملف الرئيسي يحتوي على:
- تكوين Flask
- تعريف المسارات (Routes)
- معالجات Socket.IO
- معالجات الأخطاء

### database.py
يحتوي على:
- نماذج SQLAlchemy
- `Room` - نموذج الغرفة
- `Player` - نموذج اللاعب
- دوال مساعدة لتوليد الأرقام العشوائية

### config.py
إعدادات التطبيق:
- إعدادات قاعدة البيانات
- إعدادات Flask
- إعدادات Socket.IO
- ثوابت اللعبة

### templates/
قوالب HTML:
- `base.html` - القالب الأساسي
- `index.html` - الصفحة الرئيسية
- `create_room.html` - إنشاء غرفة
- `join_room.html` - الانضمام لغرفة
- `waiting_room.html` - غرفة الانتظار

### static/
ملفات ثابتة:
- `css/style.css` - الأنماط العامة
- `js/script.js` - الدوال المساعدة

## الأوامر المفيدة

### تهيئة قاعدة البيانات
```bash
flask --app app init-db
```

### إعادة تعيين قاعدة البيانات
```bash
flask --app app reset-db
```

### إدخال shell للتطبيق
```bash
flask --app app shell
```

## الاختبار

### اختبار يدوي:

1. **فتح صفحة واحدة**:
   - تفتح `http://localhost:5000`
   - انقر "إنشاء غرفة"
   - أدخل اسمك
   - انسخ رمز الغرفة

2. **فتح صفحة ثانية** (في نافذة browser مختلفة أو incognito):
   - تفتح `http://localhost:5000`
   - انقر "الانضمام"
   - أدخل رمز الغرفة واسمك
   - اضغط الانضمام

3. **اختبار العمل**:
   - تأكد من أن قائمة اللاعبين تحدثت في الصفحتين
   - في الصفحة الأولى (المضيف) اضغط "بدء اللعبة"
   - تأكد من أن كلا الصفحتين استقبلت رسالة البدء

## Debugging

### إظهار معلومات الأخطاء:

أضف إلى app.py:
```python
app.config['PROPAGATE_EXCEPTIONS'] = True
app.logger.setLevel(logging.DEBUG)
```

### طباعة Logs:
```python
print("Debug message:", variable)
app.logger.info("Info message")
app.logger.error("Error message")
```

### فحص قاعدة البيانات:

داخل shell:
```python
from app import db
from database import Room, Player

# عرض جميع الغرف
rooms = Room.query.all()

# عرض جميع اللاعبين
players = Player.query.all()

# حذف جميع البيانات
db.drop_all()
db.create_all()
```

## الميزات القادمة

### التطويرات المخطط لها:

1. **توزيع الأدوار**:
   - إضافة دالة توزيع عشوائية
   - عرض الدور في صفحة سرية
   - حماية معلومات الأدوار

2. **نظام اللعب**:
   - نظام يوم/ليل
   - دور الشرطي والطبيب
   - نظام التصويت

3. **التحسينات**:
   - إضافة صوت
   - رسائل بين اللاعبين
   - إحصائيات اللعبة
   - نظام الترتيب

## ملاحظات مهمة

1. **الأمان**: لا تنسى إضافة authentication وتشفير في الإنتاج
2. **الأداء**: استخدم قاعدة بيانات أقوى في الإنتاج (PostgreSQL)
3. **الأخطاء**: تعامل مع كل الأخطاء المحتملة
4. **الأداء**: استخدم caching للبيانات المتكررة

## الموارد والمراجع

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [Socket.IO](https://socket.io/docs/v4/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)

---

استمتع بالتطوير! 🚀
