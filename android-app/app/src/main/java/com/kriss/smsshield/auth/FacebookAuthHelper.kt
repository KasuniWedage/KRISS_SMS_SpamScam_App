package com.kriss.smsshield.auth

import androidx.fragment.app.FragmentActivity
import com.facebook.CallbackManager
import com.facebook.FacebookCallback
import com.facebook.FacebookException
import com.facebook.FacebookSdk
import com.facebook.login.LoginManager
import com.facebook.login.LoginResult

/**
 * Wraps Facebook Login SDK.
 *
 * SETUP REQUIRED before this works:
 *   1. Register the app at developers.facebook.com, add the Android
 *      platform (package name + release/debug key hash).
 *   2. Add facebook_app_id / facebook_client_token to strings.xml (see
 *      values/strings.xml TODO marker) and the corresponding meta-data
 *      entries in AndroidManifest.xml (already added — just fill in values).
 *
 * The accessToken is sent to the backend at POST /api/auth/facebook — the
 * backend independently re-verifies it against Facebook's Graph API
 * (debug_token + /me) before trusting anything from it.
 */
class FacebookAuthHelper(private val activity: FragmentActivity) {

    val callbackManager: CallbackManager = CallbackManager.Factory.create()

    fun login(onSuccess: (String) -> Unit, onCancel: () -> Unit, onError: (String) -> Unit) {
        if (!FacebookSdk.isInitialized()) {
            onError(activity.getString(com.kriss.smsshield.R.string.facebook_not_configured))
            return
        }
        LoginManager.getInstance().registerCallback(
            callbackManager,
            object : FacebookCallback<LoginResult> {
                override fun onSuccess(result: LoginResult) {
                    onSuccess(result.accessToken.token)
                }

                override fun onCancel() {
                    onCancel()
                }

                override fun onError(error: FacebookException) {
                    onError(error.localizedMessage ?: "Facebook sign-in failed")
                }
            }
        )
        LoginManager.getInstance().logInWithReadPermissions(activity, listOf("email", "public_profile"))
    }
}
