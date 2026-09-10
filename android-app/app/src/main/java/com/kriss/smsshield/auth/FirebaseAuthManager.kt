package com.kriss.smsshield.auth

import com.google.firebase.auth.FacebookAuthProvider
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import kotlinx.coroutines.tasks.await

/**
 * Wraps Firebase Authentication. This is the recommended path for Forgot
 * Password: sendPasswordResetEmail() is handled ENTIRELY by Firebase's own
 * infrastructure — Firebase generates the reset link, emails it, and hosts
 * the reset page. No SMTP credentials, no custom token/expiry logic, and
 * no separate ResetPasswordActivity screen are needed on our side at all.
 *
 * All sign-in methods here return a Firebase ID token via [currentIdToken],
 * which the app then POSTs to the backend's /api/auth/firebase-sync to get
 * this app's own session JWT (used for classify/history/report/etc).
 *
 * SETUP REQUIRED before this works:
 *   1. Create a project at https://console.firebase.google.com
 *   2. Add an Android app to it with package name com.kriss.smsshield
 *      (and your SHA-1 fingerprint, needed for Google Sign-In via Firebase).
 *   3. Download google-services.json and place it at
 *      android-app/app/google-services.json (replacing the placeholder).
 *   4. In the Firebase Console, enable the sign-in methods you want under
 *      Authentication -> Sign-in method: Email/Password, Google, Facebook.
 *   5. Download the Firebase Admin service-account JSON (Project Settings
 *      -> Service Accounts) and point the backend's .env
 *      FIREBASE_CREDENTIALS_PATH at it.
 */
class FirebaseAuthManager {

    private val auth: FirebaseAuth by lazy { FirebaseAuth.getInstance() }

    /** True once a Firebase session already exists (survives app restarts). */
    fun isSignedIn(): Boolean = auth.currentUser != null

    fun signOut() = auth.signOut()

    suspend fun registerWithEmail(email: String, password: String) {
        auth.createUserWithEmailAndPassword(email, password).await()
    }

    suspend fun sendEmailVerificationAndSignOut() {
        val user = auth.currentUser ?: error("No Firebase user is signed in")
        user.sendEmailVerification().await()
        auth.signOut()
    }

    suspend fun signInWithEmail(email: String, password: String) {
        auth.signInWithEmailAndPassword(email, password).await()
    }

    /**
     * The entire Forgot Password flow, in one call. Firebase looks up the
     * email, generates a secure single-use reset link, and sends it via
     * its own mail infrastructure. There is nothing else to implement.
     *
     * Note: like the custom backend flow, Firebase also does NOT reveal
     * whether the email exists — it resolves successfully either way from
     * the caller's perspective (Firebase itself throttles abuse server-side).
     */
    suspend fun sendPasswordResetEmail(email: String) {
        auth.sendPasswordResetEmail(email).await()
    }

    suspend fun signInWithGoogleIdToken(googleIdToken: String) {
        val credential = GoogleAuthProvider.getCredential(googleIdToken, null)
        auth.signInWithCredential(credential).await()
    }

    suspend fun signInWithFacebookAccessToken(facebookAccessToken: String) {
        val credential = FacebookAuthProvider.getCredential(facebookAccessToken)
        auth.signInWithCredential(credential).await()
    }

    /**
     * Fetches a fresh Firebase ID token for the currently signed-in user,
     * to send to the backend's /api/auth/firebase-sync endpoint.
     * forceRefresh=true avoids sending a stale/expired token.
     */
    suspend fun currentIdToken(forceRefresh: Boolean = true): String {
        val user = auth.currentUser ?: error("No Firebase user is signed in")
        val result = user.getIdToken(forceRefresh).await()
        return result.token ?: error("Firebase did not return an ID token")
    }

    fun currentEmail(): String? = auth.currentUser?.email
}
