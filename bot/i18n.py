"""Internationalization for the generated bot (Section 23)."""
from __future__ import annotations

SUPPORTED_LANGUAGES = [
    "ar",
    "en",
    "ru"
]
FALLBACK_LANGUAGE = "en"

STRINGS: dict[str, dict[str, str]] = {
    "ar": {
        "error.generic": "⚠️ حدث خطأ ما (مرجع {error_id}). تم إبلاغ الفريق.",
        "list.none": "لا توجد معروضات مطابقة للفلاتر.",
        "listing.pending_review": "⏳ معروضك قيد المراجعة. سنبلغك خلال 24 ساعة.",
        "menu.admin": "🛡 لوحة الإدارة",
        "menu.back": "← رجوع",
        "menu.browse": "🛍 تصفّح المعروضات",
        "menu.cancel": "❌ إلغاء",
        "menu.close": "✖ إغلاق",
        "menu.lang": "🌐 اللغة",
        "menu.my_listings": "📦 معروضاتي",
        "menu.my_orders": "🧾 طلباتي",
        "menu.profile": "👤 ملفي",
        "menu.sell": "📤 اعرض حسابك للبيع",
        "menu.support": "🆘 الدعم الفني",
        "menu.title": "🛒 <b>سوق الحسابات</b>\n\nاشترِ وبِع حسابات وقنوات وأسماء تيليجرام بأمان" + " تام مع نظام الضمان (Escrow).",
        "menu.wallet": "💎 محفظتي",
        "order.confirmed": "🎉 تم تأكيد الطلب #{id}. تم تحويل المبلغ للبائع.",
        "order.created": "تم إنشاء الطلب #{id}. الإجمالي: {total} ⭐ (عمولة {fee} ⭐).",
        "order.paid": "✅ تم استلام الدفع. أمام البائع 24 ساعة للتسليم.",
        "rate.slow": "⏳ تهدّأ قليلاً. أعد المحاولة بعد {retry} ثانية.",
        "wallet.balance": "💎 الرصيد: {balance} ⭐\n🔒 محجوز في الضمان: {locked} ⭐"
    },
    "en": {
        "error.generic": "⚠️ Something went wrong (ref {error_id}). The team was notified.",
        "list.none": "No listings match your filters.",
        "listing.pending_review": "⏳ Your listing is under review. We'll notify you within 24 h" + "ours.",
        "menu.admin": "🛡 Admin panel",
        "menu.back": "← Back",
        "menu.browse": "🛍 Browse listings",
        "menu.cancel": "❌ Cancel",
        "menu.close": "✖ Close",
        "menu.lang": "🌐 Language",
        "menu.my_listings": "📦 My listings",
        "menu.my_orders": "🧾 My orders",
        "menu.profile": "👤 Profile",
        "menu.sell": "📤 Sell an account",
        "menu.support": "🆘 Support",
        "menu.title": "🛒 <b>Accounts Marketplace</b>\n\nBuy and sell Telegram accounts, channe" + "ls, and usernames safely with escrow protection.",
        "menu.wallet": "💎 Wallet",
        "order.confirmed": "🎉 Order #{id} confirmed. Funds released to seller.",
        "order.created": "Order #{id} created. Total: {total} ⭐ (fee {fee} ⭐).",
        "order.paid": "✅ Payment received. The seller has 24h to deliver.",
        "rate.slow": "⏳ Slow down. Try again in {retry}s.",
        "wallet.balance": "💎 Balance: {balance} ⭐\n🔒 Locked in escrow: {locked} ⭐"
    },
    "ru": {
        "error.generic": "⚠️ Произошла ошибка (код {error_id}). Мы уведомлены.",
        "list.none": "Нет объявлений по вашим фильтрам.",
        "listing.pending_review": "⏳ Ваше объявление на проверке. Мы уведомим вас в течение 24 " + "часов.",
        "menu.admin": "🛡 Админ-панель",
        "menu.back": "← Назад",
        "menu.browse": "🛍 Просмотр объявлений",
        "menu.cancel": "❌ Отмена",
        "menu.close": "✖ Закрыть",
        "menu.lang": "🌐 Язык",
        "menu.my_listings": "📦 Мои объявления",
        "menu.my_orders": "🧾 Мои заказы",
        "menu.profile": "👤 Профиль",
        "menu.sell": "📤 Продать аккаунт",
        "menu.support": "🆘 Поддержка",
        "menu.title": "🛒 <b>Маркетплейс аккаунтов</b>\n\nПокупайте и продавайте аккаунты Teleg" + "ram, каналы и юзернеймы с гарантией (эскроу).",
        "menu.wallet": "💎 Кошелёк",
        "order.confirmed": "🎉 Заказ #{id} подтверждён. Средства переведены продавцу.",
        "order.created": "Заказ #{id} создан. Итого: {total} ⭐ (комиссия {fee} ⭐).",
        "order.paid": "✅ Оплата получена. У продавца 24 часа на передачу.",
        "rate.slow": "⏳ Слишком часто. Повторите через {retry} сек.",
        "wallet.balance": "💎 Баланс: {balance} ⭐\n🔒 В эскроу: {locked} ⭐"
    }
}


def t(lang: str, key: str, **fmt) -> str:
    """Translate key for lang, falling back to 'en', then to the key itself."""
    table = STRINGS.get(lang) or {}
    value = table.get(key)
    if value is None:
        value = (STRINGS.get(FALLBACK_LANGUAGE) or {}).get(key)
    if value is None:
        return key
    if fmt:
        try:
            return value.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def plural_category(lang: str, n: int) -> str:
    """CLDR plural category (subset covering the common languages)."""
    base = str(lang or "en").split("-")[0].lower()
    n = abs(int(n))
    if base == "ar":
        if n == 0:
            return "zero"
        if n == 1:
            return "one"
        if n == 2:
            return "two"
        mod100 = n % 100
        if 3 <= mod100 <= 10:
            return "few"
        if 11 <= mod100 <= 99:
            return "many"
        return "other"
    if base in ("ru", "uk", "be", "sr", "hr", "bs"):
        mod10, mod100 = n % 10, n % 100
        if mod10 == 1 and mod100 != 11:
            return "one"
        if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
            return "few"
        return "many"
    if base == "pl":
        if n == 1:
            return "one"
        mod10, mod100 = n % 10, n % 100
        if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
            return "few"
        return "many"
    if base in ("fr", "pt", "hi", "fa", "ur"):
        return "one" if n in (0, 1) else "other"
    if base == "he":
        if n == 1:
            return "one"
        if n == 2:
            return "two"
        return "other"
    if base in ("id", "ja", "ko", "vi", "th", "zh", "tr", "az"):
        return "other"
    return "one" if n == 1 else "other"


def t_plural(lang: str, key: str, n: int, **fmt) -> str:
    """Plural-aware translation: tries key.<category>, key.other, key.

    Define strings as 'apples.one', 'apples.few', 'apples.other' (Arabic also
    'apples.zero', 'apples.two', 'apples.many'). {n} is available in fmt.
    """
    fmt = dict(fmt or {})
    fmt.setdefault("n", n)
    category = plural_category(lang, n)
    for candidate in (key + "." + category, key + ".other", key):
        value = t(lang, candidate, **fmt)
        if value != candidate:
            return value
    return key
