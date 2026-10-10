"""Design data emitted by Master Bot Maker — flows, screens, triggers.

Deterministic output: every mapping is sorted by key; lists keep their
declaration order because trigger precedence and edge order are semantic."""
from __future__ import annotations

FLOWS: dict[str, dict] = {
    "flw_admin_disputes": {
        "admin_only": True,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_ad_entry",
                "order": 0,
                "to": "nd_ad_query"
            },
            {
                "from": "nd_ad_query",
                "order": 1,
                "to": "nd_ad_msg"
            },
            {
                "from": "nd_ad_msg",
                "order": 2,
                "to": "nd_ad_end"
            }
        ],
        "id": "flw_admin_disputes",
        "name": "Admin Disputes",
        "nodes": {
            "nd_ad_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_ad_end",
                "label": "End",
                "type": "END"
            },
            "nd_ad_entry": {
                "cfg": {},
                "id": "nd_ad_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_ad_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "⚖️ <b>نزاعات مفتوحة</b>\n\n{open_disputes}"
                },
                "id": "nd_ad_msg",
                "label": "Show disputes",
                "type": "MESSAGE"
            },
            "nd_ad_query": {
                "cfg": {
                    "__dbcoerce": {
                        "evidence": "json",
                        "id": "int",
                        "opened_by": "bigint",
                        "order_id": "int",
                        "reason": "text",
                        "resolution_note": "text",
                        "status": "enum"
                    },
                    "limit": 10,
                    "op": "select",
                    "orderBy": "created_at ASC",
                    "resultVar": "open_disputes",
                    "table": "disputes",
                    "where": {
                        "status": "open"
                    }
                },
                "id": "nd_ad_query",
                "label": "Fetch open disputes",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": True,
        "start": "nd_ad_entry"
    },
    "flw_admin_menu": {
        "admin_only": True,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_adm_entry",
                "order": 0,
                "to": "nd_adm_auth"
            },
            {
                "from": "nd_adm_auth",
                "order": 1,
                "to": "nd_adm_screen"
            },
            {
                "from": "nd_adm_screen",
                "order": 2,
                "to": "nd_adm_end"
            }
        ],
        "id": "flw_admin_menu",
        "name": "Admin Menu",
        "nodes": {
            "nd_adm_auth": {
                "cfg": {
                    "failAction": "message",
                    "failMessage": "🚫 هذا الأمر متاح للمشرفين فقط.",
                    "require": "admin"
                },
                "id": "nd_adm_auth",
                "label": "Verify admin",
                "type": "AUTH_CHECK"
            },
            "nd_adm_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_adm_end",
                "label": "End",
                "type": "END"
            },
            "nd_adm_entry": {
                "cfg": {},
                "id": "nd_adm_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_adm_screen": {
                "cfg": {
                    "screenId": "scr_admin"
                },
                "id": "nd_adm_screen",
                "label": "Admin panel",
                "type": "SCREEN"
            }
        },
        "requires_auth": True,
        "start": "nd_adm_entry"
    },
    "flw_admin_pending": {
        "admin_only": True,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_ap_entry",
                "order": 0,
                "to": "nd_ap_query"
            },
            {
                "from": "nd_ap_query",
                "order": 1,
                "to": "nd_ap_msg"
            },
            {
                "from": "nd_ap_msg",
                "order": 2,
                "to": "nd_ap_end"
            }
        ],
        "id": "flw_admin_pending",
        "name": "Admin Pending",
        "nodes": {
            "nd_ap_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_ap_end",
                "label": "End",
                "type": "END"
            },
            "nd_ap_entry": {
                "cfg": {},
                "id": "nd_ap_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_ap_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "⏳ <b>معروضات قيد المراجعة</b>\n\n{pending_listings}\n\n/approve ID" + "  /  /reject ID"
                },
                "id": "nd_ap_msg",
                "label": "Show pending",
                "type": "MESSAGE"
            },
            "nd_ap_query": {
                "cfg": {
                    "__dbcoerce": {
                        "account_age_days": "int",
                        "category": "enum",
                        "country": "string",
                        "description": "text",
                        "has_2fa": "bool",
                        "id": "int",
                        "is_premium": "bool",
                        "phone_prefix": "string",
                        "price_stars": "bigint",
                        "published_at": "datetime",
                        "screenshots": "json",
                        "seller_id": "bigint",
                        "session_encrypted": "text",
                        "status": "enum",
                        "subscribers_count": "int",
                        "title": "string",
                        "view_count": "int"
                    },
                    "limit": 10,
                    "op": "select",
                    "orderBy": "created_at ASC",
                    "resultVar": "pending_listings",
                    "table": "accounts",
                    "where": {
                        "status": "pending_review"
                    }
                },
                "id": "nd_ap_query",
                "label": "Fetch pending listings",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": True,
        "start": "nd_ap_entry"
    },
    "flw_admin_stats": {
        "admin_only": True,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_as_entry",
                "order": 0,
                "to": "nd_as_q1"
            },
            {
                "from": "nd_as_q1",
                "order": 1,
                "to": "nd_as_q2"
            },
            {
                "from": "nd_as_q2",
                "order": 2,
                "to": "nd_as_q3"
            },
            {
                "from": "nd_as_q3",
                "order": 3,
                "to": "nd_as_msg"
            },
            {
                "from": "nd_as_msg",
                "order": 4,
                "to": "nd_as_end"
            }
        ],
        "id": "flw_admin_stats",
        "name": "Admin Stats",
        "nodes": {
            "nd_as_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_as_end",
                "label": "End",
                "type": "END"
            },
            "nd_as_entry": {
                "cfg": {},
                "id": "nd_as_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_as_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "📊 <b>إحصائيات المنصة</b>\n\nمعروضات: {accounts_count}\nطلبات: {or" + "ders_count}\nنزاعات مفتوحة: {disputes_count}"
                },
                "id": "nd_as_msg",
                "label": "Show stats",
                "type": "MESSAGE"
            },
            "nd_as_q1": {
                "cfg": {
                    "__dbcoerce": {
                        "account_age_days": "int",
                        "category": "enum",
                        "country": "string",
                        "description": "text",
                        "has_2fa": "bool",
                        "id": "int",
                        "is_premium": "bool",
                        "phone_prefix": "string",
                        "price_stars": "bigint",
                        "published_at": "datetime",
                        "screenshots": "json",
                        "seller_id": "bigint",
                        "session_encrypted": "text",
                        "status": "enum",
                        "subscribers_count": "int",
                        "title": "string",
                        "view_count": "int"
                    },
                    "op": "count",
                    "resultVar": "accounts_count",
                    "table": "accounts"
                },
                "id": "nd_as_q1",
                "label": "Count accounts",
                "type": "DB_QUERY"
            },
            "nd_as_q2": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "op": "count",
                    "resultVar": "orders_count",
                    "table": "orders"
                },
                "id": "nd_as_q2",
                "label": "Count orders",
                "type": "DB_QUERY"
            },
            "nd_as_q3": {
                "cfg": {
                    "__dbcoerce": {
                        "evidence": "json",
                        "id": "int",
                        "opened_by": "bigint",
                        "order_id": "int",
                        "reason": "text",
                        "resolution_note": "text",
                        "status": "enum"
                    },
                    "op": "count",
                    "resultVar": "disputes_count",
                    "table": "disputes",
                    "where": {
                        "status": "open"
                    }
                },
                "id": "nd_as_q3",
                "label": "Count disputes",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": True,
        "start": "nd_as_entry"
    },
    "flw_auto_release": {
        "admin_only": False,
        "backable": False,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_ar_entry",
                "order": 0,
                "to": "nd_ar_find"
            },
            {
                "from": "nd_ar_find",
                "order": 1,
                "to": "nd_ar_release"
            },
            {
                "from": "nd_ar_release",
                "order": 2,
                "to": "nd_ar_count"
            },
            {
                "from": "nd_ar_count",
                "order": 3,
                "to": "nd_ar_notify"
            },
            {
                "from": "nd_ar_notify",
                "order": 4,
                "to": "nd_ar_end"
            }
        ],
        "id": "flw_auto_release",
        "name": "Auto Release Escrow",
        "nodes": {
            "nd_ar_count": {
                "cfg": {
                    "expression": "@expr.len(@input.expired_orders)",
                    "variable": "released_count"
                },
                "id": "nd_ar_count",
                "label": "Count released",
                "type": "COMPUTE"
            },
            "nd_ar_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_ar_end",
                "label": "End",
                "type": "END"
            },
            "nd_ar_entry": {
                "cfg": {},
                "id": "nd_ar_entry",
                "label": "Scheduled entry",
                "type": "TRIGGER"
            },
            "nd_ar_find": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "limit": 100,
                    "op": "select",
                    "orderBy": "created_at ASC",
                    "resultVar": "expired_orders",
                    "table": "orders",
                    "where": {
                        "status": "delivered"
                    }
                },
                "id": "nd_ar_find",
                "label": "Find delivered orders past AUTO_RELEASE_HOURS",
                "type": "DB_QUERY"
            },
            "nd_ar_notify": {
                "cfg": {
                    "chatId": "@env.SUPPORT_CHAT_ID",
                    "text": "♻️ Auto-release executed.\nReleased orders: {released_count}"
                },
                "id": "nd_ar_notify",
                "label": "Notify support channel",
                "type": "MESSAGE"
            },
            "nd_ar_release": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "fields": {
                        "seller_paid_at": "@expr.now()",
                        "status": "confirmed"
                    },
                    "op": "update",
                    "resultVar": "released_count",
                    "table": "orders",
                    "where": {
                        "status": "delivered"
                    }
                },
                "id": "nd_ar_release",
                "label": "Release escrow to seller",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": False,
        "start": "nd_ar_entry"
    },
    "flw_browse_filter": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_bf_entry",
                "order": 0,
                "to": "nd_bf_parse"
            },
            {
                "from": "nd_bf_parse",
                "order": 1,
                "to": "nd_bf_query"
            },
            {
                "from": "nd_bf_query",
                "order": 2,
                "to": "nd_bf_summary"
            },
            {
                "from": "nd_bf_summary",
                "order": 3,
                "to": "nd_bf_msg"
            },
            {
                "from": "nd_bf_msg",
                "order": 4,
                "to": "nd_bf_end"
            }
        ],
        "id": "flw_browse_filter",
        "name": "Browse Filter",
        "nodes": {
            "nd_bf_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_bf_end",
                "label": "End",
                "type": "END"
            },
            "nd_bf_entry": {
                "cfg": {},
                "id": "nd_bf_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_bf_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "🛍 <b>نتائج التصفية</b>\n\n{browse_summary}\n\nاضغط زراً للتصفية م" + "رة أخرى."
                },
                "id": "nd_bf_msg",
                "label": "Show results",
                "type": "MESSAGE"
            },
            "nd_bf_parse": {
                "cfg": {
                    "expression": "@expr.re.search('(?:cat|sort):(.+)', @ctx.callback_data).gro" + "up(1)",
                    "variable": "filter_value"
                },
                "id": "nd_bf_parse",
                "label": "Extract filter value",
                "type": "COMPUTE"
            },
            "nd_bf_query": {
                "cfg": {
                    "__dbcoerce": {
                        "account_age_days": "int",
                        "category": "enum",
                        "country": "string",
                        "description": "text",
                        "has_2fa": "bool",
                        "id": "int",
                        "is_premium": "bool",
                        "phone_prefix": "string",
                        "price_stars": "bigint",
                        "published_at": "datetime",
                        "screenshots": "json",
                        "seller_id": "bigint",
                        "session_encrypted": "text",
                        "status": "enum",
                        "subscribers_count": "int",
                        "title": "string",
                        "view_count": "int"
                    },
                    "limit": 10,
                    "op": "select",
                    "orderBy": "price_stars ASC",
                    "resultVar": "browse_results",
                    "table": "accounts",
                    "where": {
                        "status": "active"
                    }
                },
                "id": "nd_bf_query",
                "label": "Query listings",
                "type": "DB_QUERY"
            },
            "nd_bf_summary": {
                "cfg": {
                    "expression": "@expr.format_orders(@input.browse_results)",
                    "variable": "browse_summary"
                },
                "id": "nd_bf_summary",
                "label": "Format summary",
                "type": "COMPUTE"
            }
        },
        "requires_auth": True,
        "start": "nd_bf_entry"
    },
    "flw_browse_menu": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_br_entry",
                "order": 0,
                "to": "nd_br_screen"
            },
            {
                "from": "nd_br_screen",
                "order": 1,
                "to": "nd_br_wait"
            },
            {
                "from": "nd_br_wait",
                "order": 2,
                "to": "nd_br_end"
            }
        ],
        "id": "flw_browse_menu",
        "name": "Browse",
        "nodes": {
            "nd_br_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_br_end",
                "label": "End",
                "type": "END"
            },
            "nd_br_entry": {
                "cfg": {},
                "id": "nd_br_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_br_screen": {
                "cfg": {
                    "screenId": "scr_browse"
                },
                "id": "nd_br_screen",
                "label": "Browse categories",
                "type": "SCREEN"
            },
            "nd_br_wait": {
                "cfg": {
                    "expect": "callback",
                    "screenId": "scr_browse",
                    "timeoutSeconds": 600,
                    "variable": "browse_filter"
                },
                "id": "nd_br_wait",
                "label": "Wait for category",
                "type": "SEND_AND_WAIT"
            }
        },
        "requires_auth": True,
        "start": "nd_br_entry"
    },
    "flw_buy": {
        "admin_only": False,
        "backable": False,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_buy_entry",
                "order": 0,
                "to": "nd_buy_parse"
            },
            {
                "from": "nd_buy_parse",
                "order": 1,
                "to": "nd_buy_fetch"
            },
            {
                "from": "nd_buy_fetch",
                "order": 2,
                "to": "nd_buy_check_status"
            },
            {
                "from": "nd_buy_check_status",
                "order": 3,
                "to": "nd_buy_fee"
            },
            {
                "from": "nd_buy_fee",
                "order": 4,
                "to": "nd_buy_total"
            },
            {
                "from": "nd_buy_total",
                "order": 5,
                "to": "nd_buy_show_confirm"
            },
            {
                "from": "nd_buy_show_confirm",
                "order": 6,
                "to": "nd_buy_invoice"
            },
            {
                "from": "nd_buy_invoice",
                "order": 7,
                "to": "nd_buy_end"
            }
        ],
        "id": "flw_buy",
        "name": "Buy Account",
        "nodes": {
            "nd_buy_check_status": {
                "cfg": {
                    "expression": "@expr.int(@input.account_row[0][\"price_stars\"])",
                    "variable": "price"
                },
                "id": "nd_buy_check_status",
                "label": "Extract price & seller",
                "type": "COMPUTE"
            },
            "nd_buy_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_buy_end",
                "label": "End",
                "type": "END"
            },
            "nd_buy_entry": {
                "cfg": {},
                "id": "nd_buy_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_buy_fee": {
                "cfg": {
                    "expression": "@expr.int(@input.price * int(@env.PLATFORM_FEE_PERCENT) / 10" + "0)",
                    "variable": "fee"
                },
                "id": "nd_buy_fee",
                "label": "Compute platform fee",
                "type": "COMPUTE"
            },
            "nd_buy_fetch": {
                "cfg": {
                    "__dbcoerce": {
                        "account_age_days": "int",
                        "category": "enum",
                        "country": "string",
                        "description": "text",
                        "has_2fa": "bool",
                        "id": "int",
                        "is_premium": "bool",
                        "phone_prefix": "string",
                        "price_stars": "bigint",
                        "published_at": "datetime",
                        "screenshots": "json",
                        "seller_id": "bigint",
                        "session_encrypted": "text",
                        "status": "enum",
                        "subscribers_count": "int",
                        "title": "string",
                        "view_count": "int"
                    },
                    "limit": 1,
                    "op": "select",
                    "resultVar": "account_row",
                    "table": "accounts",
                    "where": {
                        "id": "@input.account_id"
                    }
                },
                "id": "nd_buy_fetch",
                "label": "Fetch account",
                "type": "DB_QUERY"
            },
            "nd_buy_invoice": {
                "cfg": {
                    "amount": "@input.total",
                    "currency": "XTR",
                    "description": "دفع مضمون عبر الضمان",
                    "payload": "order:acct:{account_id}",
                    "stars": True,
                    "startParam": "escrow_order",
                    "title": "شراء حساب تيليجرام"
                },
                "id": "nd_buy_invoice",
                "label": "Send invoice",
                "type": "PAYMENT"
            },
            "nd_buy_parse": {
                "cfg": {
                    "expression": "@expr.int(@expr.re_group('account_id', @ctx.callback_data))",
                    "variable": "account_id"
                },
                "id": "nd_buy_parse",
                "label": "Parse account_id from callback",
                "type": "COMPUTE"
            },
            "nd_buy_show_confirm": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "🛒 <b>تأكيد الشراء</b>\n\nالعرض: {account_row[0][\"title\"]}\nالسع" + "ر: {price} ⭐\nعمولة المنصة: {fee} ⭐\n<b>الإجمالي: {total} ⭐</b>\n" + "\n⚠️ <b>سيتم حجز المبلغ في الضمان</b> ولن يُسلَّم للبائع حتى تؤكّد" + " استلامك."
                },
                "id": "nd_buy_show_confirm",
                "label": "Show confirmation",
                "type": "MESSAGE"
            },
            "nd_buy_total": {
                "cfg": {
                    "expression": "@input.price + @input.fee",
                    "variable": "total"
                },
                "id": "nd_buy_total",
                "label": "Total",
                "type": "COMPUTE"
            }
        },
        "requires_auth": True,
        "start": "nd_buy_entry"
    },
    "flw_dispute": {
        "admin_only": False,
        "backable": True,
        "cooldown": 120,
        "edges": [
            {
                "from": "nd_dis_entry",
                "order": 0,
                "to": "nd_dis_order"
            },
            {
                "from": "nd_dis_order",
                "order": 1,
                "to": "nd_dis_reason"
            },
            {
                "from": "nd_dis_reason",
                "order": 2,
                "to": "nd_dis_insert"
            },
            {
                "from": "nd_dis_insert",
                "order": 3,
                "to": "nd_dis_update_order"
            },
            {
                "from": "nd_dis_update_order",
                "order": 4,
                "to": "nd_dis_notify"
            },
            {
                "from": "nd_dis_notify",
                "order": 5,
                "to": "nd_dis_confirm"
            },
            {
                "from": "nd_dis_confirm",
                "order": 6,
                "to": "nd_dis_end"
            }
        ],
        "id": "flw_dispute",
        "name": "Dispute",
        "nodes": {
            "nd_dis_confirm": {
                "cfg": {
                    "text": "✅ تم فتح النزاع #{dispute_id}.\n\nسيقوم فريق الدعم بمراجعة الطلب خ" + "لال 24 ساعة. المبلغ محجوز حتى الحل."
                },
                "id": "nd_dis_confirm",
                "label": "Confirm to user",
                "type": "MESSAGE"
            },
            "nd_dis_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_dis_end",
                "label": "End",
                "type": "END"
            },
            "nd_dis_entry": {
                "cfg": {},
                "id": "nd_dis_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_dis_insert": {
                "cfg": {
                    "__dbcoerce": {
                        "evidence": "json",
                        "id": "int",
                        "opened_by": "bigint",
                        "order_id": "int",
                        "reason": "text",
                        "resolution_note": "text",
                        "status": "enum"
                    },
                    "fields": {
                        "opened_by": "@ctx.user_id",
                        "order_id": "@input.order_id",
                        "reason": "@input.reason",
                        "status": "open"
                    },
                    "op": "insert",
                    "resultVar": "dispute_id",
                    "table": "disputes"
                },
                "id": "nd_dis_insert",
                "label": "Create dispute",
                "type": "DB_QUERY"
            },
            "nd_dis_notify": {
                "cfg": {
                    "chatId": "@env.SUPPORT_CHAT_ID",
                    "parseMode": "HTML",
                    "text": "⚠️ <b>نزاع جديد</b>\n\nنزاع #{dispute_id}\nالطلب: #{order_id}\nمن:" + " {ctx.first_name}\n\nالسبب:\n{reason}"
                },
                "id": "nd_dis_notify",
                "label": "Notify admins",
                "type": "MESSAGE"
            },
            "nd_dis_order": {
                "cfg": {
                    "inputType": "number",
                    "prompt": "🆘 <b>فتح نزاع</b>\n\nما رقم الطلب الذي تريد فتح نزاع بشأنه؟",
                    "timeoutSeconds": 300,
                    "variable": "order_id"
                },
                "id": "nd_dis_order",
                "label": "Which order?",
                "type": "ASK"
            },
            "nd_dis_reason": {
                "cfg": {
                    "errorMessage": "❌ الشرح قصير جداً أو طويل جداً.",
                    "inputType": "text",
                    "prompt": "اشرح المشكلة بالتفصيل (20-1000 حرف):",
                    "timeoutSeconds": 600,
                    "validation": "^.{20,1000}$",
                    "variable": "reason"
                },
                "id": "nd_dis_reason",
                "label": "Reason",
                "type": "ASK"
            },
            "nd_dis_update_order": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "fields": {
                        "dispute_reason": "@input.reason",
                        "status": "disputed"
                    },
                    "op": "update",
                    "resultVar": "updated_orders",
                    "table": "orders",
                    "where": {
                        "id": "@input.order_id"
                    }
                },
                "id": "nd_dis_update_order",
                "label": "Mark order disputed",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": True,
        "start": "nd_dis_entry"
    },
    "flw_main_menu": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_main_entry",
                "order": 0,
                "to": "nd_main_ensure_wallet"
            },
            {
                "from": "nd_main_ensure_wallet",
                "order": 1,
                "to": "nd_main_screen"
            },
            {
                "from": "nd_main_screen",
                "order": 2,
                "to": "nd_main_end"
            }
        ],
        "id": "flw_main_menu",
        "name": "Main Menu",
        "nodes": {
            "nd_main_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_main_end",
                "label": "End",
                "type": "END"
            },
            "nd_main_ensure_wallet": {
                "cfg": {
                    "__dbcoerce": {
                        "balance_stars": "bigint",
                        "id": "int",
                        "lifetime_earned": "bigint",
                        "lifetime_spent": "bigint",
                        "locked_stars": "bigint",
                        "user_id": "bigint"
                    },
                    "fields": {
                        "balance_stars": 0,
                        "locked_stars": 0,
                        "user_id": "@ctx.user_id"
                    },
                    "op": "insert",
                    "resultVar": "wallet_id",
                    "table": "wallets"
                },
                "id": "nd_main_ensure_wallet",
                "label": "Ensure wallet exists",
                "type": "DB_QUERY"
            },
            "nd_main_entry": {
                "cfg": {},
                "id": "nd_main_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_main_screen": {
                "cfg": {
                    "screenId": "scr_main_menu"
                },
                "id": "nd_main_screen",
                "label": "Main menu",
                "type": "SCREEN"
            }
        },
        "requires_auth": True,
        "start": "nd_main_entry"
    },
    "flw_my_orders": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_mo_entry",
                "order": 0,
                "to": "nd_mo_fetch"
            },
            {
                "from": "nd_mo_fetch",
                "order": 1,
                "to": "nd_mo_build_summary"
            },
            {
                "from": "nd_mo_build_summary",
                "order": 2,
                "to": "nd_mo_screen"
            },
            {
                "from": "nd_mo_screen",
                "order": 3,
                "to": "nd_mo_end"
            }
        ],
        "id": "flw_my_orders",
        "name": "My Orders",
        "nodes": {
            "nd_mo_build_summary": {
                "cfg": {
                    "expression": "@expr.format_orders(@input.my_orders)",
                    "variable": "my_orders_summary"
                },
                "id": "nd_mo_build_summary",
                "label": "Build summary",
                "type": "COMPUTE"
            },
            "nd_mo_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_mo_end",
                "label": "End",
                "type": "END"
            },
            "nd_mo_entry": {
                "cfg": {},
                "id": "nd_mo_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_mo_fetch": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "limit": 10,
                    "op": "select",
                    "orderBy": "created_at DESC",
                    "resultVar": "my_orders",
                    "table": "orders",
                    "where": {
                        "buyer_id": "@ctx.user_id"
                    }
                },
                "id": "nd_mo_fetch",
                "label": "Fetch orders",
                "type": "DB_QUERY"
            },
            "nd_mo_screen": {
                "cfg": {
                    "screenId": "scr_my_orders"
                },
                "id": "nd_mo_screen",
                "label": "Show orders",
                "type": "SCREEN"
            }
        },
        "requires_auth": True,
        "start": "nd_mo_entry"
    },
    "flw_order_paid": {
        "admin_only": False,
        "backable": False,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_op_entry",
                "order": 0,
                "to": "nd_op_parse_payload"
            },
            {
                "from": "nd_op_parse_payload",
                "order": 1,
                "to": "nd_op_create_order"
            },
            {
                "from": "nd_op_create_order",
                "order": 2,
                "to": "nd_op_lock_escrow"
            },
            {
                "from": "nd_op_lock_escrow",
                "order": 3,
                "to": "nd_op_notify_seller"
            },
            {
                "from": "nd_op_notify_seller",
                "order": 4,
                "to": "nd_op_end"
            }
        ],
        "id": "flw_order_paid",
        "name": "Order Paid (Escrow Locked)",
        "nodes": {
            "nd_op_create_order": {
                "cfg": {
                    "__dbcoerce": {
                        "account_id": "int",
                        "buyer_confirmed_at": "datetime",
                        "buyer_id": "bigint",
                        "dispute_reason": "text",
                        "escrow_charge_id": "string",
                        "fee_stars": "bigint",
                        "id": "int",
                        "net_to_seller_stars": "bigint",
                        "notes": "text",
                        "price_stars": "bigint",
                        "seller_id": "bigint",
                        "seller_paid_at": "datetime",
                        "status": "enum"
                    },
                    "fields": {
                        "account_id": "@input.account_id",
                        "buyer_id": "@ctx.user_id",
                        "escrow_charge_id": "@ctx.payment.charge_id",
                        "price_stars": "@ctx.payment.amount",
                        "status": "paid_escrow"
                    },
                    "op": "insert",
                    "resultVar": "order_id",
                    "table": "orders"
                },
                "id": "nd_op_create_order",
                "label": "Create order",
                "type": "DB_QUERY"
            },
            "nd_op_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_op_end",
                "label": "End",
                "type": "END"
            },
            "nd_op_entry": {
                "cfg": {},
                "id": "nd_op_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_op_lock_escrow": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "✅ <b>تم استلام دفعك</b>\n\nرقم الطلب: #{order_id}\n\n📌 البائع ملز" + "َم بتسليم بيانات الحساب خلال <b>24 ساعة</b>.\nإذا لم يستجب، سيُستر" + "د المبلغ تلقائياً.\n\n🆘 استخدم /dispute إذا واجهت مشكلة."
                },
                "id": "nd_op_lock_escrow",
                "label": "Notify buyer",
                "type": "MESSAGE"
            },
            "nd_op_notify_seller": {
                "cfg": {
                    "chatId": "@ctx.user_id",
                    "parseMode": "HTML",
                    "text": "🔔 <b>طلب جديد على معروضك!</b>\n\nرقم الطلب: #{order_id}\nالمبلغ ا" + "لمحجوز: {ctx.payment.amount} ⭐\n\n📌 سلّم بيانات الحساب للمشتري خل" + "ال 24 ساعة لتحصل على المبلغ.\nاستخدم: /deliver {order_id}"
                },
                "id": "nd_op_notify_seller",
                "label": "DM buyer (TODO: route to seller)",
                "type": "MESSAGE"
            },
            "nd_op_parse_payload": {
                "cfg": {
                    "expression": "@expr.int(@expr.re_group('account_id', @ctx.payment.payload," + " 'order:acct:(\\\\d+)'))",
                    "variable": "account_id"
                },
                "id": "nd_op_parse_payload",
                "label": "Parse account_id from payload",
                "type": "COMPUTE"
            }
        },
        "requires_auth": True,
        "start": "nd_op_entry"
    },
    "flw_profile_lang": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_pl_entry",
                "order": 0,
                "to": "nd_pl_msg"
            },
            {
                "from": "nd_pl_msg",
                "order": 1,
                "to": "nd_pl_end"
            }
        ],
        "id": "flw_profile_lang",
        "name": "Profile Language",
        "nodes": {
            "nd_pl_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_pl_end",
                "label": "End",
                "type": "END"
            },
            "nd_pl_entry": {
                "cfg": {},
                "id": "nd_pl_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_pl_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "🌐 <b>اختر اللغة</b>\n\nأرسل: ar / en / ru"
                },
                "id": "nd_pl_msg",
                "label": "Show language picker",
                "type": "MESSAGE"
            }
        },
        "requires_auth": True,
        "start": "nd_pl_entry"
    },
    "flw_sell_start": {
        "admin_only": False,
        "backable": True,
        "cooldown": 30,
        "edges": [
            {
                "from": "nd_sell_entry",
                "order": 0,
                "to": "nd_sell_category"
            },
            {
                "from": "nd_sell_category",
                "order": 1,
                "to": "nd_sell_title"
            },
            {
                "from": "nd_sell_title",
                "order": 2,
                "to": "nd_sell_desc"
            },
            {
                "from": "nd_sell_desc",
                "order": 3,
                "to": "nd_sell_price"
            },
            {
                "from": "nd_sell_price",
                "order": 4,
                "to": "nd_sell_validate_price"
            },
            {
                "from": "nd_sell_validate_price",
                "order": 5,
                "to": "nd_sell_check_min"
            },
            {
                "condition": "@input.price >= int(@env.MIN_LISTING_PRICE)",
                "from": "nd_sell_check_min",
                "order": 6,
                "to": "nd_sell_check_max"
            },
            {
                "from": "nd_sell_check_min",
                "order": 7,
                "to": "nd_sell_reject_price"
            },
            {
                "condition": "@input.price <= int(@env.MAX_LISTING_PRICE)",
                "from": "nd_sell_check_max",
                "order": 8,
                "to": "nd_sell_age"
            },
            {
                "from": "nd_sell_check_max",
                "order": 9,
                "to": "nd_sell_reject_price"
            },
            {
                "from": "nd_sell_age",
                "order": 10,
                "to": "nd_sell_country"
            },
            {
                "from": "nd_sell_country",
                "order": 11,
                "to": "nd_sell_phone"
            },
            {
                "from": "nd_sell_phone",
                "order": 12,
                "to": "nd_sell_premium"
            },
            {
                "from": "nd_sell_premium",
                "order": 13,
                "to": "nd_sell_2fa"
            },
            {
                "from": "nd_sell_2fa",
                "order": 14,
                "to": "nd_sell_session"
            },
            {
                "from": "nd_sell_session",
                "order": 15,
                "to": "nd_sell_confirm"
            },
            {
                "from": "nd_sell_confirm",
                "order": 16,
                "to": "nd_sell_encrypt"
            },
            {
                "from": "nd_sell_encrypt",
                "order": 17,
                "to": "nd_sell_insert"
            },
            {
                "from": "nd_sell_insert",
                "order": 18,
                "to": "nd_sell_notify_admins"
            },
            {
                "from": "nd_sell_notify_admins",
                "order": 19,
                "to": "nd_sell_confirm_user"
            },
            {
                "from": "nd_sell_confirm_user",
                "order": 20,
                "to": "nd_sell_end"
            },
            {
                "from": "nd_sell_reject_price",
                "order": 21,
                "to": "nd_sell_end_abort"
            }
        ],
        "id": "flw_sell_start",
        "name": "Sell — Wizard",
        "nodes": {
            "nd_sell_2fa": {
                "cfg": {
                    "errorMessage": "❌ أرسل yes أو no.",
                    "inputType": "text",
                    "prompt": "9️⃣ هل الحساب محمي بكلمة مرور (2FA)؟ أرسل yes أو no:",
                    "timeoutSeconds": 600,
                    "validation": "^(yes|no|نعم|لا)$",
                    "variable": "has_2fa_str"
                },
                "id": "nd_sell_2fa",
                "label": "Has 2FA?",
                "type": "ASK"
            },
            "nd_sell_age": {
                "cfg": {
                    "inputType": "number",
                    "prompt": "5️⃣ كم عمر الحساب بالأيام؟ (أرسل رقماً، 0 إن كنت لا تعرف)",
                    "timeoutSeconds": 600,
                    "variable": "account_age_days"
                },
                "id": "nd_sell_age",
                "label": "Account age",
                "type": "ASK"
            },
            "nd_sell_category": {
                "cfg": {
                    "errorMessage": "❌ قيمة غير صحيحة. أرسل واحدة من القيم المذكورة.",
                    "inputType": "text",
                    "prompt": "1️⃣ ما نوع ما تعرضه؟\n\nأرسل واحداً من:\n• <code>account</code> " + "— حساب\n• <code>channel</code> — قناة\n• <code>bot</code> — بوت" + "\n• <code>premium_gift</code> — هدية بريميوم\n• <code>username</" + "code> — يوزر",
                    "timeoutSeconds": 600,
                    "validation": "^(account|channel|bot|premium_gift|username)$",
                    "variable": "category"
                },
                "id": "nd_sell_category",
                "label": "Category",
                "type": "ASK"
            },
            "nd_sell_check_max": {
                "cfg": {},
                "id": "nd_sell_check_max",
                "label": "price <= MAX?",
                "type": "CONDITION"
            },
            "nd_sell_check_min": {
                "cfg": {},
                "id": "nd_sell_check_min",
                "label": "price >= MIN?",
                "type": "CONDITION"
            },
            "nd_sell_confirm": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "📝 <b>مراجعة نهائية</b>\n\n• الفئة: {category}\n• العنوان: {title}" + "\n• الوصف: {description}\n• السعر: {price} ⭐\n• العمر: {account_ag" + "e_days} يوم\n• الدولة: {country}\n• بريميوم: {is_premium_str}\n• 2" + "FA: {has_2fa_str}\n\nسيتم إرسال العرض للمراجعة الآن."
                },
                "id": "nd_sell_confirm",
                "label": "Confirm",
                "type": "MESSAGE"
            },
            "nd_sell_confirm_user": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "{t:listing.pending_review}\n\nمعرّف العرض: #{listing_id}"
                },
                "id": "nd_sell_confirm_user",
                "label": "Confirm to user",
                "type": "MESSAGE"
            },
            "nd_sell_country": {
                "cfg": {
                    "errorMessage": "❌ أرسل رمزاً دولياً مكوناً من حرفين (مثلاً SA).",
                    "inputType": "text",
                    "prompt": "6️⃣ رمز الدولة (مثلاً SA, EG, US):",
                    "timeoutSeconds": 600,
                    "validation": "^[A-Za-z]{2}$",
                    "variable": "country"
                },
                "id": "nd_sell_country",
                "label": "Country",
                "type": "ASK"
            },
            "nd_sell_desc": {
                "cfg": {
                    "errorMessage": "❌ الوصف يجب أن يكون بين 10 و1500 حرف.",
                    "inputType": "text",
                    "prompt": "3️⃣ أرسل وصفاً تفصيلياً (10-1500 حرف):",
                    "timeoutSeconds": 600,
                    "validation": "^.{10,1500}$",
                    "variable": "description"
                },
                "id": "nd_sell_desc",
                "label": "Description",
                "type": "ASK"
            },
            "nd_sell_encrypt": {
                "cfg": {
                    "expression": "@expr.encrypt_session(@input.session_string)",
                    "variable": "session_encrypted"
                },
                "id": "nd_sell_encrypt",
                "label": "Encrypt session (Fernet)",
                "type": "COMPUTE"
            },
            "nd_sell_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_sell_end",
                "label": "End",
                "type": "END"
            },
            "nd_sell_end_abort": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_sell_end_abort",
                "label": "Abort",
                "type": "END"
            },
            "nd_sell_entry": {
                "cfg": {},
                "id": "nd_sell_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_sell_insert": {
                "cfg": {
                    "__dbcoerce": {
                        "account_age_days": "int",
                        "category": "enum",
                        "country": "string",
                        "description": "text",
                        "has_2fa": "bool",
                        "id": "int",
                        "is_premium": "bool",
                        "phone_prefix": "string",
                        "price_stars": "bigint",
                        "published_at": "datetime",
                        "screenshots": "json",
                        "seller_id": "bigint",
                        "session_encrypted": "text",
                        "status": "enum",
                        "subscribers_count": "int",
                        "title": "string",
                        "view_count": "int"
                    },
                    "fields": {
                        "account_age_days": "@input.account_age_days",
                        "category": "@input.category",
                        "country": "@input.country",
                        "description": "@input.description",
                        "has_2fa": "@expr.is_yes(@input.has_2fa_str)",
                        "is_premium": "@expr.is_yes(@input.is_premium_str)",
                        "phone_prefix": "@input.phone_prefix",
                        "price_stars": "@input.price",
                        "seller_id": "@ctx.user_id",
                        "session_encrypted": "@input.session_encrypted",
                        "status": "pending_review",
                        "title": "@input.title"
                    },
                    "op": "insert",
                    "resultVar": "listing_id",
                    "table": "accounts"
                },
                "id": "nd_sell_insert",
                "label": "Insert listing",
                "type": "DB_QUERY"
            },
            "nd_sell_notify_admins": {
                "cfg": {
                    "chatId": "@env.SUPPORT_CHAT_ID",
                    "parseMode": "HTML",
                    "text": "🔔 <b>عرض جديد للمراجعة</b>\n\nمعرّف: #{listing_id}\nمن: {ctx.firs" + "t_name} (@{ctx.username})\nالفئة: {category}\nالسعر: {price} ⭐\n\n" + "/approve {listing_id}\n/reject {listing_id}"
                },
                "id": "nd_sell_notify_admins",
                "label": "Notify admins",
                "type": "MESSAGE"
            },
            "nd_sell_phone": {
                "cfg": {
                    "errorMessage": "❌ أرسل 1-4 أرقام فقط.",
                    "inputType": "text",
                    "prompt": "7️⃣ أول 3 أرقام من رقم الهاتف (للمعاينة فقط، لن يُنشر كاملاً):",
                    "timeoutSeconds": 600,
                    "validation": "^\\+?\\d{1,4}$",
                    "variable": "phone_prefix"
                },
                "id": "nd_sell_phone",
                "label": "Phone prefix",
                "type": "ASK"
            },
            "nd_sell_premium": {
                "cfg": {
                    "errorMessage": "❌ أرسل yes أو no.",
                    "inputType": "text",
                    "prompt": "8️⃣ هل الحساب بريميوم؟ أرسل yes أو no:",
                    "timeoutSeconds": 600,
                    "validation": "^(yes|no|نعم|لا)$",
                    "variable": "is_premium_str"
                },
                "id": "nd_sell_premium",
                "label": "Is Premium?",
                "type": "ASK"
            },
            "nd_sell_price": {
                "cfg": {
                    "inputType": "number",
                    "prompt": "4️⃣ أرسل السعر بالنجوم ⭐ (بين 100 و 50000):",
                    "timeoutSeconds": 600,
                    "variable": "price_input"
                },
                "id": "nd_sell_price",
                "label": "Price",
                "type": "ASK"
            },
            "nd_sell_reject_price": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "❌ السعر خارج النطاق المسموح.\n\nالحد الأدنى: {env.MIN_LISTING_PRIC" + "E} ⭐\nالحد الأقصى: {env.MAX_LISTING_PRICE} ⭐\n\nأعد /sell وابدأ من" + " جديد."
                },
                "id": "nd_sell_reject_price",
                "label": "Reject price",
                "type": "MESSAGE"
            },
            "nd_sell_session": {
                "cfg": {
                    "errorMessage": "❌ بيانات الجلسة غير صالحة.",
                    "inputType": "text",
                    "prompt": "🔐 <b>أرسل بيانات الجلسة المشفّرة</b>\n\n(سلسلة Telethon StringS" + "ession أو Pyrogram Session)\n\nسيتم تشفيرها فوراً قبل التخزين.\n" + "\n⚠️ <b>تحذير:</b> أرسلها فقط عندما تكون مستعداً — سيتم حجزها حت" + "ى إتمام الصفقة.",
                    "timeoutSeconds": 900,
                    "validation": "^.{20,}$",
                    "variable": "session_string"
                },
                "id": "nd_sell_session",
                "label": "Session string",
                "type": "ASK"
            },
            "nd_sell_title": {
                "cfg": {
                    "errorMessage": "❌ العنوان يجب أن يكون بين 3 و100 حرف.",
                    "inputType": "text",
                    "prompt": "2️⃣ أرسل عنواناً جاذباً للعرض (3-100 حرف):",
                    "timeoutSeconds": 600,
                    "validation": "^.{3,100}$",
                    "variable": "title"
                },
                "id": "nd_sell_title",
                "label": "Title",
                "type": "ASK"
            },
            "nd_sell_validate_price": {
                "cfg": {
                    "expression": "int(@input.price_input)",
                    "variable": "price"
                },
                "id": "nd_sell_validate_price",
                "label": "Validate price",
                "type": "COMPUTE"
            }
        },
        "requires_auth": True,
        "start": "nd_sell_entry"
    },
    "flw_support": {
        "admin_only": False,
        "backable": True,
        "cooldown": 60,
        "edges": [
            {
                "from": "nd_sup_entry",
                "order": 0,
                "to": "nd_sup_screen"
            },
            {
                "from": "nd_sup_screen",
                "order": 1,
                "to": "nd_sup_wait"
            },
            {
                "from": "nd_sup_wait",
                "order": 2,
                "to": "nd_sup_end"
            }
        ],
        "id": "flw_support",
        "name": "Support",
        "nodes": {
            "nd_sup_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_sup_end",
                "label": "End",
                "type": "END"
            },
            "nd_sup_entry": {
                "cfg": {},
                "id": "nd_sup_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_sup_screen": {
                "cfg": {
                    "screenId": "scr_support"
                },
                "id": "nd_sup_screen",
                "label": "Support menu",
                "type": "SCREEN"
            },
            "nd_sup_wait": {
                "cfg": {
                    "expect": "callback",
                    "screenId": "scr_support",
                    "timeoutSeconds": 600,
                    "variable": "support_action"
                },
                "id": "nd_sup_wait",
                "label": "Wait for action",
                "type": "SEND_AND_WAIT"
            }
        },
        "requires_auth": True,
        "start": "nd_sup_entry"
    },
    "flw_support_ticket": {
        "admin_only": False,
        "backable": True,
        "cooldown": 60,
        "edges": [
            {
                "from": "nd_st_entry",
                "order": 0,
                "to": "nd_st_ask"
            },
            {
                "from": "nd_st_ask",
                "order": 1,
                "to": "nd_st_insert"
            },
            {
                "from": "nd_st_insert",
                "order": 2,
                "to": "nd_st_msg"
            },
            {
                "from": "nd_st_msg",
                "order": 3,
                "to": "nd_st_end"
            }
        ],
        "id": "flw_support_ticket",
        "name": "Support Ticket",
        "nodes": {
            "nd_st_ask": {
                "cfg": {
                    "errorMessage": "❌ يجب أن يكون بين 10 و 500 حرف.",
                    "inputType": "text",
                    "prompt": "📨 أرسل موضوع تذكرتك + وصفها (مثلاً: 'مشكلة دفع - الطلب #123 لم " + "يُسلَّم')",
                    "timeoutSeconds": 600,
                    "validation": "^.{10,500}$",
                    "variable": "ticket_text"
                },
                "id": "nd_st_ask",
                "label": "Ask for ticket text",
                "type": "ASK"
            },
            "nd_st_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_st_end",
                "label": "End",
                "type": "END"
            },
            "nd_st_entry": {
                "cfg": {},
                "id": "nd_st_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_st_insert": {
                "cfg": {
                    "__dbcoerce": {
                        "admin_reply": "text",
                        "id": "int",
                        "message": "text",
                        "status": "enum",
                        "subject": "string",
                        "user_id": "bigint"
                    },
                    "fields": {
                        "message": "@input.ticket_text",
                        "status": "open",
                        "subject": "@input.ticket_text",
                        "user_id": "@ctx.user_id"
                    },
                    "op": "insert",
                    "resultVar": "ticket_id",
                    "table": "support_tickets"
                },
                "id": "nd_st_insert",
                "label": "Create ticket",
                "type": "DB_QUERY"
            },
            "nd_st_msg": {
                "cfg": {
                    "text": "✅ تم فتح التذكرة #{ticket_id}.\n\nسيتواصل معك فريق الدعم في أقرب و" + "قت."
                },
                "id": "nd_st_msg",
                "label": "Confirm",
                "type": "MESSAGE"
            }
        },
        "requires_auth": True,
        "start": "nd_st_entry"
    },
    "flw_topup_success": {
        "admin_only": False,
        "backable": False,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_ts_entry",
                "order": 0,
                "to": "nd_ts_fetch_wallet"
            },
            {
                "from": "nd_ts_fetch_wallet",
                "order": 1,
                "to": "nd_ts_credit"
            },
            {
                "from": "nd_ts_credit",
                "order": 2,
                "to": "nd_ts_log"
            },
            {
                "from": "nd_ts_log",
                "order": 3,
                "to": "nd_ts_msg"
            },
            {
                "from": "nd_ts_msg",
                "order": 4,
                "to": "nd_ts_end"
            }
        ],
        "id": "flw_topup_success",
        "name": "Topup Success",
        "nodes": {
            "nd_ts_credit": {
                "cfg": {
                    "__dbcoerce": {
                        "balance_stars": "bigint",
                        "id": "int",
                        "lifetime_earned": "bigint",
                        "lifetime_spent": "bigint",
                        "locked_stars": "bigint",
                        "user_id": "bigint"
                    },
                    "fields": {
                        "balance_stars": "@expr.int(@input.wallet_row[0][\"balance_stars\"]) + " + "@ctx.payment.amount"
                    },
                    "op": "update",
                    "resultVar": "updated_wallets",
                    "table": "wallets",
                    "where": {
                        "user_id": "@ctx.user_id"
                    }
                },
                "id": "nd_ts_credit",
                "label": "Credit wallet",
                "type": "DB_QUERY"
            },
            "nd_ts_end": {
                "cfg": {
                    "clearState": True
                },
                "id": "nd_ts_end",
                "label": "End",
                "type": "END"
            },
            "nd_ts_entry": {
                "cfg": {},
                "id": "nd_ts_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_ts_fetch_wallet": {
                "cfg": {
                    "__dbcoerce": {
                        "balance_stars": "bigint",
                        "id": "int",
                        "lifetime_earned": "bigint",
                        "lifetime_spent": "bigint",
                        "locked_stars": "bigint",
                        "user_id": "bigint"
                    },
                    "limit": 1,
                    "op": "select",
                    "resultVar": "wallet_row",
                    "table": "wallets",
                    "where": {
                        "user_id": "@ctx.user_id"
                    }
                },
                "id": "nd_ts_fetch_wallet",
                "label": "Fetch wallet row",
                "type": "DB_QUERY"
            },
            "nd_ts_log": {
                "cfg": {
                    "__dbcoerce": {
                        "amount": "bigint",
                        "balance_after": "bigint",
                        "charge_id": "string",
                        "id": "int",
                        "kind": "enum",
                        "note": "string",
                        "order_id": "int",
                        "user_id": "bigint"
                    },
                    "fields": {
                        "amount": "@ctx.payment.amount",
                        "balance_after": 0,
                        "charge_id": "@ctx.payment.charge_id",
                        "kind": "topup",
                        "note": "Topup via Stars",
                        "user_id": "@ctx.user_id"
                    },
                    "op": "insert",
                    "resultVar": "tx_id",
                    "table": "wallet_tx"
                },
                "id": "nd_ts_log",
                "label": "Log transaction",
                "type": "DB_QUERY"
            },
            "nd_ts_msg": {
                "cfg": {
                    "text": "✅ تم إيداع {ctx.payment.amount} ⭐ في محفظتك.\n\nاستخدم /wallet لعر" + "ض الرصيد."
                },
                "id": "nd_ts_msg",
                "label": "Confirm to user",
                "type": "MESSAGE"
            }
        },
        "requires_auth": True,
        "start": "nd_ts_entry"
    },
    "flw_wallet": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_w_entry",
                "order": 0,
                "to": "nd_w_fetch"
            },
            {
                "from": "nd_w_fetch",
                "order": 1,
                "to": "nd_w_set_vars"
            },
            {
                "from": "nd_w_set_vars",
                "order": 2,
                "to": "nd_w_screen"
            },
            {
                "from": "nd_w_screen",
                "order": 3,
                "to": "nd_w_end"
            }
        ],
        "id": "flw_wallet",
        "name": "Wallet",
        "nodes": {
            "nd_w_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_w_end",
                "label": "End",
                "type": "END"
            },
            "nd_w_entry": {
                "cfg": {},
                "id": "nd_w_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_w_fetch": {
                "cfg": {
                    "__dbcoerce": {
                        "balance_stars": "bigint",
                        "id": "int",
                        "lifetime_earned": "bigint",
                        "lifetime_spent": "bigint",
                        "locked_stars": "bigint",
                        "user_id": "bigint"
                    },
                    "limit": 1,
                    "op": "select",
                    "resultVar": "wallet_row",
                    "table": "wallets",
                    "where": {
                        "user_id": "@ctx.user_id"
                    }
                },
                "id": "nd_w_fetch",
                "label": "Fetch wallet",
                "type": "DB_QUERY"
            },
            "nd_w_screen": {
                "cfg": {
                    "screenId": "scr_wallet"
                },
                "id": "nd_w_screen",
                "label": "Show wallet",
                "type": "SCREEN"
            },
            "nd_w_set_vars": {
                "cfg": {
                    "expression": "@input.wallet_row[0][\"balance_stars\"] if @input.wallet_row" + " else 0",
                    "variable": "balance"
                },
                "id": "nd_w_set_vars",
                "label": "Extract balance",
                "type": "COMPUTE"
            }
        },
        "requires_auth": True,
        "start": "nd_w_entry"
    },
    "flw_wallet_history": {
        "admin_only": False,
        "backable": True,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_wh_entry",
                "order": 0,
                "to": "nd_wh_query"
            },
            {
                "from": "nd_wh_query",
                "order": 1,
                "to": "nd_wh_msg"
            },
            {
                "from": "nd_wh_msg",
                "order": 2,
                "to": "nd_wh_end"
            }
        ],
        "id": "flw_wallet_history",
        "name": "Wallet History",
        "nodes": {
            "nd_wh_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_wh_end",
                "label": "End",
                "type": "END"
            },
            "nd_wh_entry": {
                "cfg": {},
                "id": "nd_wh_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_wh_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "📜 <b>آخر العمليات</b>\n\n{tx_history}\n\n(أحدث 10 عمليات)"
                },
                "id": "nd_wh_msg",
                "label": "Show history",
                "type": "MESSAGE"
            },
            "nd_wh_query": {
                "cfg": {
                    "__dbcoerce": {
                        "amount": "bigint",
                        "balance_after": "bigint",
                        "charge_id": "string",
                        "id": "int",
                        "kind": "enum",
                        "note": "string",
                        "order_id": "int",
                        "user_id": "bigint"
                    },
                    "limit": 10,
                    "op": "select",
                    "orderBy": "created_at DESC",
                    "resultVar": "tx_history",
                    "table": "wallet_tx",
                    "where": {
                        "user_id": "@ctx.user_id"
                    }
                },
                "id": "nd_wh_query",
                "label": "Fetch last 10 tx",
                "type": "DB_QUERY"
            }
        },
        "requires_auth": True,
        "start": "nd_wh_entry"
    },
    "flw_wallet_topup": {
        "admin_only": False,
        "backable": False,
        "cooldown": 0,
        "edges": [
            {
                "from": "nd_wt_entry",
                "order": 0,
                "to": "nd_wt_invoice"
            },
            {
                "from": "nd_wt_invoice",
                "order": 1,
                "to": "nd_wt_end"
            }
        ],
        "id": "flw_wallet_topup",
        "name": "Wallet Top-up Invoice",
        "nodes": {
            "nd_wt_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_wt_end",
                "label": "End",
                "type": "END"
            },
            "nd_wt_entry": {
                "cfg": {},
                "id": "nd_wt_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_wt_invoice": {
                "cfg": {
                    "amount": 100,
                    "currency": "XTR",
                    "description": "Add 100 Stars to your wallet",
                    "payload": "topup:100",
                    "stars": True,
                    "startParam": "topup",
                    "title": "Wallet top-up"
                },
                "id": "nd_wt_invoice",
                "label": "Send topup invoice",
                "type": "PAYMENT"
            }
        },
        "requires_auth": True,
        "start": "nd_wt_entry"
    },
    "flw_wallet_withdraw": {
        "admin_only": False,
        "backable": True,
        "cooldown": 30,
        "edges": [
            {
                "from": "nd_ww_entry",
                "order": 0,
                "to": "nd_ww_msg"
            },
            {
                "from": "nd_ww_msg",
                "order": 1,
                "to": "nd_ww_end"
            }
        ],
        "id": "flw_wallet_withdraw",
        "name": "Wallet Withdraw",
        "nodes": {
            "nd_ww_end": {
                "cfg": {
                    "clearState": False
                },
                "id": "nd_ww_end",
                "label": "End",
                "type": "END"
            },
            "nd_ww_entry": {
                "cfg": {},
                "id": "nd_ww_entry",
                "label": "Entry",
                "type": "TRIGGER"
            },
            "nd_ww_msg": {
                "cfg": {
                    "parseMode": "HTML",
                    "text": "💸 <b>سحب من المحفظة</b>\n\nأرسل المبلغ المطلوب سحبه (بالنجوم). سي" + "تم تحويل طلبك إلى فريق الدعم للمراجعة."
                },
                "id": "nd_ww_msg",
                "label": "Ask for amount",
                "type": "MESSAGE"
            }
        },
        "requires_auth": True,
        "start": "nd_ww_entry"
    }
}


SCREENS: dict[str, dict] = {
    "scr_admin": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_adm_pending",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "admin:pending",
                    "switch_inline": "",
                    "target": "",
                    "text": "⏳ قيد المراجعة",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_adm_disputes",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "admin:disputes",
                    "switch_inline": "",
                    "target": "",
                    "text": "⚖️ نزاعات",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_adm_stats",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "admin:stats",
                    "switch_inline": "",
                    "target": "",
                    "text": "📊 إحصائيات",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my8",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_admin",
        "media_source": "",
        "media_type": "",
        "message": "🛡 <b>لوحة الإدارة</b>\n\nاختر العملية:",
        "name": "Admin Panel",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_browse": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_cat_acc",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "cat:account",
                    "switch_inline": "",
                    "target": "",
                    "text": "👤 حسابات",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_cat_ch",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "cat:channel",
                    "switch_inline": "",
                    "target": "",
                    "text": "📢 قنوات",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_cat_bot",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "cat:bot",
                    "switch_inline": "",
                    "target": "",
                    "text": "🤖 بوتات",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_cat_prem",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "cat:premium_gift",
                    "switch_inline": "",
                    "target": "",
                    "text": "⭐ بريميوم",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_cat_un",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "cat:username",
                    "switch_inline": "",
                    "target": "",
                    "text": "📛 يوزرات",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_sort_price",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "sort:price_asc",
                    "switch_inline": "",
                    "target": "",
                    "text": "💎 الأرخص أولاً",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_main",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_browse",
        "media_source": "",
        "media_type": "",
        "message": "🛍 <b>تصفّح المعروضات</b>\n\nاختر الفئة للتصفية:",
        "name": "Browse Listings",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_main_menu": {
        "backable": False,
        "buttons": [
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_browse",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_browse",
                    "text": "{t:menu.browse}",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_sell",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_sell_start",
                    "text": "{t:menu.sell}",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_my_lis",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_my_listings",
                    "text": "{t:menu.my_listings}",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_my_ord",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_my_orders",
                    "text": "{t:menu.my_orders}",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_wallet",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_wallet",
                    "text": "{t:menu.wallet}",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_support",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_support",
                    "text": "{t:menu.support}",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_profile",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_profile",
                    "text": "{t:menu.profile}",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_admin",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_admin",
                    "text": "{t:menu.admin}",
                    "url": "",
                    "visible_if": "ctx.is_admin"
                }
            ]
        ],
        "id": "scr_main_menu",
        "media_source": "",
        "media_type": "",
        "message": "{t:menu.title}",
        "name": "Main Menu",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_my_listings": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_new_listing",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_sell_start",
                    "text": "➕ معروض جديد",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my3",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_my_listings",
        "media_source": "",
        "media_type": "",
        "message": "📦 <b>معروضاتي</b>\n\n{my_listings_summary}",
        "name": "My Listings",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_my_orders": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my4",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_my_orders",
        "media_source": "",
        "media_type": "",
        "message": "🧾 <b>طلباتي</b>\n\n{my_orders_summary}",
        "name": "My Orders",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_profile": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_lang",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "profile:lang",
                    "switch_inline": "",
                    "target": "",
                    "text": "{t:menu.lang}",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my7",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_profile",
        "media_source": "",
        "media_type": "",
        "message": "👤 <b>ملفي</b>\n\nالاسم: {ctx.first_name}\nالمعرّف: <code>{ctx.user_id}</co" + "de>\nاللغة: {ctx.language}\n\nنقاط البائع: {seller_rating} ⭐ ({reviews_coun" + "t} تقييم)",
        "name": "Profile",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_sell_start": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_sell_go",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "sell:start",
                    "switch_inline": "",
                    "target": "",
                    "text": "▶️ ابدأ",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_main2",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_sell_start",
        "media_source": "",
        "media_type": "",
        "message": "📤 <b>عرض حساب للبيع</b>\n\nسيتم سؤالك عن تفاصيل الحساب خطوة بخطوة.\n\n⚠️ <" + "b>مهم:</b> يتم تشفير بيانات الجلسة قبل التخزين. لا يُسلَّم شيء للمشتري حتى " + "تدفع المنصة.",
        "name": "Sell — Start",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_support": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_open_ticket",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "support:new",
                    "switch_inline": "",
                    "target": "",
                    "text": "📨 فتح تذكرة",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my6",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_support",
        "media_source": "",
        "media_type": "",
        "message": "🆘 <b>الدعم الفني</b>\n\nأرسل استفسارك وسيرد عليك فريقنا في أقرب وقت.",
        "name": "Support",
        "next_on_text": "",
        "parse_mode": "HTML"
    },
    "scr_wallet": {
        "backable": True,
        "buttons": [
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_topup",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "wallet:topup",
                    "switch_inline": "",
                    "target": "",
                    "text": "➕ إيداع نجوم",
                    "url": "",
                    "visible_if": ""
                },
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_withdraw",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "wallet:withdraw",
                    "switch_inline": "",
                    "target": "",
                    "text": "💸 سحب",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "callback",
                    "copy_text": "",
                    "id": "btn_history",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "wallet:history",
                    "switch_inline": "",
                    "target": "",
                    "text": "📜 سجل العمليات",
                    "url": "",
                    "visible_if": ""
                }
            ],
            [
                {
                    "action": "navigate",
                    "copy_text": "",
                    "id": "btn_back_my5",
                    "input_prompt": "",
                    "input_timeout": 300,
                    "input_type": "text",
                    "input_validation": "",
                    "input_var": "",
                    "kind": "inline",
                    "pay_amount": "",
                    "payload": "",
                    "switch_inline": "",
                    "target": "scr_main_menu",
                    "text": "{t:menu.back}",
                    "url": "",
                    "visible_if": ""
                }
            ]
        ],
        "id": "scr_wallet",
        "media_source": "",
        "media_type": "",
        "message": "{t:wallet.balance}",
        "name": "Wallet",
        "next_on_text": "",
        "parse_mode": "HTML"
    }
}


TRIGGERS: list[dict] = [
    {
        "admin_only": True,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_admin_menu",
        "id": "trg_admin",
        "kind": "command",
        "name": "/admin",
        "pattern": "admin",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_browse_menu",
        "id": "trg_browse",
        "kind": "command",
        "name": "/browse",
        "pattern": "browse",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_dispute",
        "id": "trg_dispute",
        "kind": "command",
        "name": "/dispute",
        "pattern": "dispute",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_my_orders",
        "id": "trg_orders",
        "kind": "command",
        "name": "/orders",
        "pattern": "orders",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_sell_start",
        "id": "trg_sell",
        "kind": "command",
        "name": "/sell",
        "pattern": "sell",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_main_menu",
        "id": "trg_start",
        "kind": "command",
        "name": "/start",
        "pattern": "start",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_support",
        "id": "trg_support",
        "kind": "command",
        "name": "/support",
        "pattern": "support",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_wallet",
        "id": "trg_wallet",
        "kind": "command",
        "name": "/wallet",
        "pattern": "wallet",
        "premium_only": False,
        "prio": 0,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": True,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_admin_disputes",
        "id": "trg_admin_disputes",
        "kind": "callback",
        "name": "admin disputes",
        "pattern": "admin:disputes",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "admin"
    },
    {
        "admin_only": True,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_admin_pending",
        "id": "trg_admin_pending",
        "kind": "callback",
        "name": "admin pending",
        "pattern": "admin:pending",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "admin"
    },
    {
        "admin_only": True,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_admin_stats",
        "id": "trg_admin_stats",
        "kind": "callback",
        "name": "admin stats",
        "pattern": "admin:stats",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "admin"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_browse_filter",
        "id": "trg_cat",
        "kind": "callback",
        "name": "browse category",
        "pattern": "cat:",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_browse_filter",
        "id": "trg_sort",
        "kind": "callback",
        "name": "browse sort",
        "pattern": "sort:",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_buy",
        "id": "trg_buy_cb",
        "kind": "callback",
        "name": "buy-callback",
        "pattern": "buy:",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_profile_lang",
        "id": "trg_profile_lang",
        "kind": "callback",
        "name": "profile language",
        "pattern": "profile:lang",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 30,
        "filters": [],
        "flow_id": "flw_sell_start",
        "id": "trg_sell_start_btn",
        "kind": "callback",
        "name": "sell wizard start",
        "pattern": "sell:start",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_support_ticket",
        "id": "trg_support_new",
        "kind": "callback",
        "name": "support new ticket",
        "pattern": "support:new",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_wallet_history",
        "id": "trg_wallet_history_btn",
        "kind": "callback",
        "name": "wallet history btn",
        "pattern": "wallet:history",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_wallet_topup",
        "id": "trg_wallet_topup_btn",
        "kind": "callback",
        "name": "wallet topup btn",
        "pattern": "wallet:topup",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_wallet_withdraw",
        "id": "trg_wallet_withdraw_btn",
        "kind": "callback",
        "name": "wallet withdraw btn",
        "pattern": "wallet:withdraw",
        "premium_only": False,
        "prio": 1,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_order_paid",
        "id": "trg_order_payment",
        "kind": "successful_payment",
        "name": "order payment",
        "pattern": "order:",
        "premium_only": False,
        "prio": 7,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    },
    {
        "admin_only": False,
        "channels": [],
        "cooldown": 0,
        "filters": [],
        "flow_id": "flw_topup_success",
        "id": "trg_wallet_topup",
        "kind": "successful_payment",
        "name": "wallet topup",
        "pattern": "topup",
        "premium_only": False,
        "prio": 7,
        "rate_count": 0,
        "rate_per": 0,
        "scope": "any"
    }
]


I18N_ENABLED: bool = True


MENU_COMMANDS: list[dict] = [
    {
        "command": "admin",
        "description": "لوحة الإدارة"
    },
    {
        "command": "browse",
        "description": "تصفّح المعروضات"
    },
    {
        "command": "cancel",
        "description": "إلغاء العملية"
    },
    {
        "command": "dispute",
        "description": "فتح نزاع"
    },
    {
        "command": "help",
        "description": "المساعدة"
    },
    {
        "command": "orders",
        "description": "طلباتي"
    },
    {
        "command": "sell",
        "description": "اعرض حسابك للبيع"
    },
    {
        "command": "start",
        "description": "القائمة الرئيسية"
    },
    {
        "command": "support",
        "description": "الدعم الفني"
    },
    {
        "command": "wallet",
        "description": "محفظتي"
    }
]
