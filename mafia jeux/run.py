#!/usr/bin/env python3
"""
Mafia Online - Game Server
لعبة المافيا الإلكترونية - خادم اللعبة
"""

import os
import sys
from app import create_app, socketio

def main():
    """نقطة الدخول الرئيسية للتطبيق"""
    # إنشاء التطبيق
    app = create_app()

    # إعدادات التشغيل
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    print("🎭 Mafia Online - Game Server")
    print("=" * 40)
    print(f"🌐 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🐛 Debug: {debug}")
    print("=" * 40)

    # تشغيل الخادم
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            log_output=debug
        )
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف الخادم بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطأ في تشغيل الخادم: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
