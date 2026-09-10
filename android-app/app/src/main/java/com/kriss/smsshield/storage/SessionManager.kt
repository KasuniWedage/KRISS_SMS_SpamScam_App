package com.kriss.smsshield.storage

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys

class SessionManager(context: Context) {
    companion object {
        @Volatile private var transientToken: String? = null
        private const val SECURE_PREFS = "kriss_secure_session"
        private const val FALLBACK_PREFS = "kriss_session_fallback"
    }

    private val appContext = context.applicationContext

    private fun getPrefs(): SharedPreferences {
        return try {
            EncryptedSharedPreferences.create(
                SECURE_PREFS,
                MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
                appContext,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (_: Throwable) {
            appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE)
        }
    }

    fun saveToken(token: String, persist: Boolean = true) {
        transientToken = token
        try {
            getPrefs().edit().putString("token", token).commit()
        } catch (_: Throwable) {}
        try {
            appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE)
                .edit().putString("token", token).commit()
        } catch (_: Throwable) {}
    }

    fun token(): String? {
        if (!transientToken.isNullOrBlank()) return transientToken
        val stored = try { getPrefs().getString("token", null) } catch (_: Throwable) { null }
        if (!stored.isNullOrBlank()) {
            transientToken = stored
            return stored
        }
        val fallback = try {
            appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).getString("token", null)
        } catch (_: Throwable) { null }
        if (!fallback.isNullOrBlank()) {
            transientToken = fallback
            return fallback
        }
        return null
    }

    fun saveRole(role: String) {
        try { getPrefs().edit().putString("role", role).commit() } catch (_: Throwable) {}
        try { appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).edit().putString("role", role).commit() } catch (_: Throwable) {}
    }

    fun role(): String {
        return try {
            getPrefs().getString("role", null)
                ?: appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).getString("role", "user")
                ?: "user"
        } catch (_: Throwable) {
            "user"
        }
    }

    fun saveRememberedEmail(email: String?) {
        val editor1 = try { getPrefs().edit() } catch (_: Throwable) { null }
        val editor2 = appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).edit()
        if (email.isNullOrBlank()) {
            editor1?.remove("remembered_email")?.commit()
            editor2.remove("remembered_email").commit()
        } else {
            editor1?.putString("remembered_email", email)?.commit()
            editor2.putString("remembered_email", email).commit()
        }
    }

    fun rememberedEmail(): String? {
        return try {
            getPrefs().getString("remembered_email", null)
                ?: appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).getString("remembered_email", null)
        } catch (_: Throwable) {
            null
        }
    }

    fun saveNotificationsEnabled(enabled: Boolean) {
        try { getPrefs().edit().putBoolean("notifications_enabled", enabled).commit() } catch (_: Throwable) {}
        try { appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).edit().putBoolean("notifications_enabled", enabled).commit() } catch (_: Throwable) {}
    }

    fun notificationsEnabled(): Boolean {
        return try {
            getPrefs().getBoolean("notifications_enabled", true)
        } catch (_: Throwable) {
            true
        }
    }

    fun clear() {
        transientToken = null
        try { getPrefs().edit().remove("token").remove("role").commit() } catch (_: Throwable) {}
        try { appContext.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE).edit().remove("token").remove("role").commit() } catch (_: Throwable) {}
    }
}
