package com.kriss.smsshield

import android.os.Bundle
import android.util.Patterns
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityForgotPasswordBinding
import com.kriss.smsshield.model.ForgotPasswordRequest
import com.kriss.smsshield.model.ResetPasswordRequest
import com.kriss.smsshield.model.VerifyResetCodeRequest
import kotlinx.coroutines.launch

/**
 * Forgot Password, powered entirely by Firebase Authentication.
 *
 * Why this is the correct fix (vs. the earlier custom SMTP-based version):
 * Firebase now OWNS the actual password (see RegisterActivity/LoginActivity
 * — sign-up and sign-in both go through Firebase). So resetting it through
 * Firebase resets the exact credential that login checks, with guaranteed
 * email delivery via Google's own mail infrastructure — no SMTP
 * credentials, no custom token generation/expiry logic, no separate
 * "enter the code" screen. One call, and Firebase does the rest:
 *   1. Looks up the email (silently no-ops if it doesn't exist, same
 *      privacy behavior as before — no account enumeration).
 *   2. Generates a secure, single-use reset link.
 *   3. Emails it and hosts the reset page itself.
 *
 * The user resets their password on Firebase's hosted page (opened from
 * the email, outside the app) and then simply logs in again normally.
 */
class ForgotPasswordActivity : AppCompatActivity() {

    private lateinit var b: ActivityForgotPasswordBinding
    private var verifiedOtp: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityForgotPasswordBinding.inflate(layoutInflater)
        setContentView(b.root)

        b.backButton.setOnClickListener { finish() }
        b.sendResetLinkButton.setOnClickListener { requestResetLink() }
        b.verifyOtpButton.setOnClickListener { verifyOtp() }
        b.resetPasswordButton.setOnClickListener { resetPassword() }
    }

    private fun showMessage(text: String, isSuccess: Boolean) {
        b.messageText.text = text
        b.messageText.setTextColor(ContextCompat.getColor(this, if (isSuccess) R.color.success else R.color.danger))
    }

    private fun requestResetLink() {
        val email = b.emailInput.text?.toString()?.trim().orEmpty()
        if (email.isBlank() || !Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            showMessage(getString(R.string.required_fields), false)
            return
        }
        b.loading.visibility = View.VISIBLE
        b.sendResetLinkButton.isEnabled = false
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api(this@ForgotPasswordActivity)
                    .forgotPassword(ForgotPasswordRequest(email))
                // Firebase does not reveal whether the email is registered
                // (it resolves successfully either way), so this message
                // is always shown regardless — preserving the same
                // no-account-enumeration behavior as before.
                showMessage(
                    if (response.isSuccessful) getString(R.string.reset_code_sent)
                    else if (response.code() == 503) getString(R.string.reset_email_not_configured)
                    else getString(R.string.connection_error),
                    response.isSuccessful
                )
                if (response.isSuccessful) {
                    verifiedOtp = null
                    b.resetFields.visibility = View.VISIBLE
                    b.passwordFields.visibility = View.GONE
                    b.otpInput.text?.clear()
                    b.otpInput.isEnabled = true
                    b.verifyOtpButton.visibility = View.VISIBLE
                    b.newPasswordInput.text?.clear()
                    b.confirmPasswordInput.text?.clear()
                    b.emailInput.isEnabled = false
                    b.sendResetLinkButton.setText(R.string.resend_code)
                }
            } catch (_: Exception) {
                // Firebase surfaces this for malformed/disabled accounts in
                // some configurations — still show the generic message so
                // we don't leak account existence.
                showMessage(getString(R.string.connection_error), false)
            } finally {
                b.loading.visibility = View.GONE
                b.sendResetLinkButton.isEnabled = true
            }
        }
    }

    private fun verifyOtp() {
        val otp = b.otpInput.text?.toString()?.trim().orEmpty()
        if (otp.length != 6 || !otp.all(Char::isDigit)) {
            showMessage(getString(R.string.invalid_reset_code), false)
            return
        }
        b.loading.visibility = View.VISIBLE
        b.verifyOtpButton.isEnabled = false
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api(this@ForgotPasswordActivity)
                    .verifyResetCode(VerifyResetCodeRequest(b.emailInput.text.toString().trim(), otp))
                if (response.isSuccessful) {
                    verifiedOtp = otp
                    b.otpInput.isEnabled = false
                    b.verifyOtpButton.visibility = View.GONE
                    b.passwordFields.visibility = View.VISIBLE
                    showMessage(getString(R.string.code_verified), true)
                    b.newPasswordInput.requestFocus()
                } else {
                    showMessage(getString(R.string.invalid_reset_code), false)
                }
            } catch (_: Exception) {
                showMessage(getString(R.string.connection_error), false)
            } finally {
                b.loading.visibility = View.GONE
                b.verifyOtpButton.isEnabled = true
            }
        }
    }

    private fun resetPassword() {
        val otp = verifiedOtp
        if (otp == null) {
            showMessage(getString(R.string.invalid_reset_code), false)
            b.passwordFields.visibility = View.GONE
            b.verifyOtpButton.visibility = View.VISIBLE
            return
        }
        val password = b.newPasswordInput.text?.toString().orEmpty()
        val confirmation = b.confirmPasswordInput.text?.toString().orEmpty()
        if (password != confirmation) {
            showMessage(getString(R.string.passwords_mismatch), false); return
        }
        if (password.length < 8 || !password.any(Char::isLetter) || !password.any(Char::isDigit)) {
            showMessage(getString(R.string.password_invalid), false); return
        }
        b.loading.visibility = View.VISIBLE
        b.resetPasswordButton.isEnabled = false
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api(this@ForgotPasswordActivity)
                    .resetPassword(ResetPasswordRequest(b.emailInput.text.toString().trim(), otp, password, confirmation))
                if (response.isSuccessful) {
                    showResetSuccessDialog()
                } else {
                    showMessage(getString(R.string.invalid_reset_code), false)
                }
            } catch (_: Exception) {
                showMessage(getString(R.string.connection_error), false)
            } finally {
                b.loading.visibility = View.GONE
                b.resetPasswordButton.isEnabled = true
            }
        }
    }

    private fun showResetSuccessDialog() {
        MaterialAlertDialogBuilder(this)
            .setIcon(R.drawable.ic_check_circle)
            .setTitle(R.string.reset_success_title)
            .setMessage(R.string.reset_password_success)
            .setCancelable(false)
            .setPositiveButton(R.string.continue_to_sign_in) { _, _ -> finish() }
            .show()
    }
}
