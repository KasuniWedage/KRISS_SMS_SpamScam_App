package com.kriss.smsshield.auth

import android.content.Context
import android.content.Intent
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException

/**
 * Wraps Google Sign-In (com.google.android.gms:play-services-auth).
 *
 * SETUP REQUIRED before this works:
 *   1. Create an OAuth 2.0 client in Google Cloud Console -> Credentials:
 *        - an ANDROID client (package name + SHA-1 signing fingerprint)
 *        - a WEB client (this is the "server client ID" below)
 *   2. Add google-services.json. The Google Services Gradle plugin exposes
 *      its WEB client ID as the generated `default_web_client_id` resource.
 *   3. The backend verifies the idToken against this same WEB client ID
 *      (GOOGLE_OAUTH_CLIENT_ID in backend/.env) — they must match.
 *
 * The idToken (not the accessToken) is what gets sent to the backend at
 * POST /api/auth/google — the backend independently verifies its
 * signature/audience against Google before trusting anything in it.
 */
class GoogleAuthHelper(context: Context, webClientId: String) {

    private val client: GoogleSignInClient

    init {
        val options = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(webClientId)
            .requestEmail()
            .build()
        client = GoogleSignIn.getClient(context, options)
    }

    fun signInIntent(): Intent = client.signInIntent

    fun signOut() = client.signOut()

    /**
     * Call from onActivityResult / the ActivityResultLauncher callback with
     * the returned Intent data. Returns the idToken string, or null with
     * an error message via the onError callback.
     */
    fun extractIdToken(data: Intent?, onSuccess: (String) -> Unit, onError: (String) -> Unit) {
        try {
            val account = GoogleSignIn.getSignedInAccountFromIntent(data).getResult(ApiException::class.java)
            val idToken = account?.idToken
            if (idToken.isNullOrBlank()) {
                onError("No ID token returned by Google Sign-In")
            } else {
                onSuccess(idToken)
            }
        } catch (e: ApiException) {
            onError("Google sign-in failed (code ${e.statusCode})")
        }
    }
}
