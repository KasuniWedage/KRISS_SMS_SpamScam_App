package com.kriss.smsshield.api

import android.app.Activity
import android.content.Intent
import com.kriss.smsshield.LoginActivity
import com.kriss.smsshield.report.BatchHistoryStore
import com.kriss.smsshield.storage.SessionManager

/**
 * Centralizes what happens when the backend reports the session token is no longer valid
 * (HTTP 401), e.g. because it expired or the dev server restarted. Every screen that calls
 * an authenticated endpoint should route a 401 through here instead of failing silently,
 * so the user always lands back on the login screen with a clean session.
 */
object AuthGuard {
    fun redirectToLogin(activity: Activity) {
        SessionManager(activity).clear()
        activity.startActivity(Intent(activity, LoginActivity::class.java))
        activity.finish()
    }
}
