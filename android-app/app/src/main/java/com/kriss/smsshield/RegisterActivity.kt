package com.kriss.smsshield

import android.os.Bundle
import android.util.Patterns
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityRegisterBinding
import com.kriss.smsshield.model.RegisterRequest
import kotlinx.coroutines.launch
import org.json.JSONObject

/**
 * Registration now goes through Firebase Authentication rather than this
 * backend's own bcrypt password storage. Why this matters for Forgot
 * Password specifically: whichever system actually OWNS the password is
 * the one that must handle resetting it. Firebase owns it here, so
 * Firebase's built-in password reset (see ForgotPasswordActivity) resets
 * the exact same credential this screen creates and LoginActivity checks
 * — there's no mismatch between "the password that got reset" and "the
 * password that's actually checked at login".
 *
 * After Firebase creates the account, a verification email is sent. The
 * backend profile is created only after the verified user signs in.
 */
class RegisterActivity : AppCompatActivity() {
    private lateinit var b: ActivityRegisterBinding

    override fun onCreate(s: Bundle?) {
        super.onCreate(s)
        b = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.createButton.setOnClickListener { register() }
        b.backButton.setOnClickListener { finish() }
    }

    private fun showMessage(text: String, isSuccess: Boolean) {
        b.messageText.text = text
        b.messageText.setTextColor(ContextCompat.getColor(this, if (isSuccess) R.color.success else R.color.danger))
    }

    private fun register() {
        val name = b.nameInput.text.toString().trim()
        val user = b.usernameInput.text.toString().trim()
        val email = b.emailInput.text.toString().trim()
        val pass = b.passwordInput.text.toString()
        val confirm = b.confirmInput.text.toString()

        clearFieldErrors()
        var valid = true
        if (name.length < 2) { b.nameInputLayout.error = getString(R.string.name_invalid); valid = false }
        if (!USERNAME_REGEX.matches(user)) { b.usernameInputLayout.error = getString(R.string.username_invalid); valid = false }
        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) { b.emailInputLayout.error = getString(R.string.email_invalid); valid = false }
        if (!isStrongPassword(pass)) { b.passwordInputLayout.error = getString(R.string.password_strong_invalid); valid = false }
        if (pass != confirm) { b.confirmInputLayout.error = getString(R.string.passwords_mismatch); valid = false }
        if (!valid) { showMessage(getString(R.string.correct_highlighted_fields), false); return }

        b.createButton.isEnabled = false
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api(this@RegisterActivity)
                    .register(RegisterRequest(name, user, email, pass))
                if (response.isSuccessful) {
                    showMessage(getString(R.string.account_created), true)
                    b.root.postDelayed({ finish() }, 1200)
                } else {
                    showMessage(apiError(response.errorBody()?.string()), false)
                    b.createButton.isEnabled = true
                }
            } catch (e: Exception) {
                showMessage(getString(R.string.connection_error), false)
                b.createButton.isEnabled = true
            }
        }
    }

    private fun apiError(body: String?): String = try {
        JSONObject(body.orEmpty()).optString("detail").ifBlank { getString(R.string.registration_failed) }
    } catch (_: Exception) {
        getString(R.string.registration_failed)
    }

    private fun clearFieldErrors() {
        b.nameInputLayout.error = null
        b.usernameInputLayout.error = null
        b.emailInputLayout.error = null
        b.passwordInputLayout.error = null
        b.confirmInputLayout.error = null
        b.messageText.text = ""
    }

    private fun isStrongPassword(password: String): Boolean =
        password.length >= 8 && password.any(Char::isUpperCase) &&
            password.any(Char::isLowerCase) && password.any(Char::isDigit) &&
            password.any { !it.isLetterOrDigit() }

    companion object {
        private val USERNAME_REGEX = Regex("^[A-Za-z0-9_]{3,30}$")
    }
}
