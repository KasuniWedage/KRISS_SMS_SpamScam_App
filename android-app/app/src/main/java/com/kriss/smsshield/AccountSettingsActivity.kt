package com.kriss.smsshield

import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.lifecycleScope
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityAccountSettingsBinding
import com.kriss.smsshield.databinding.DialogDeleteAccountBinding
import android.view.View
import com.kriss.smsshield.model.ActivityLogItem
import com.kriss.smsshield.model.DeleteAccountRequest
import com.kriss.smsshield.model.PasswordChange
import com.kriss.smsshield.model.ProfileUpdate
import com.kriss.smsshield.report.BatchHistoryStore
import com.kriss.smsshield.storage.SessionManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.launch

class AccountSettingsActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAccountSettingsBinding
    private var allActivityLogs: List<ActivityLogItem> = emptyList()
    private var currentLogPage = 1
    private val logsPerPage = 10

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAccountSettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.backButton.setOnClickListener { finish() }
        binding.updateButton.setOnClickListener { updateProfile() }
        binding.passwordButton.setOnClickListener { changePassword() }
        binding.deleteButton.setOnClickListener { confirmDelete() }
        binding.prevLogPageButton.setOnClickListener {
            if (currentLogPage > 1) {
                currentLogPage--
                renderActivityLogPage()
            }
        }
        binding.nextLogPageButton.setOnClickListener {
            val totalPages = (allActivityLogs.size + logsPerPage - 1) / logsPerPage
            if (currentLogPage < totalPages) {
                currentLogPage++
                renderActivityLogPage()
            }
        }
        loadAccount()
        loadActivityLog()
    }

    private fun loadAccount() = lifecycleScope.launch {
        try {
            val response = RetrofitClient.api(this@AccountSettingsActivity).settings()
            if (response.code() == 401) return@launch AuthGuard.redirectToLogin(this@AccountSettingsActivity)
            response.body()?.let {
                binding.nameInput.setText(it.name)
                binding.usernameInput.setText(it.username)
                binding.emailInput.setText(it.email)
            }
        } catch (_: Exception) {
            binding.statusText.setText(R.string.connection_error)
        }
    }

    private fun updateProfile() = lifecycleScope.launch {
        val name = binding.nameInput.text?.toString()?.trim().orEmpty()
        val username = binding.usernameInput.text?.toString()?.trim().orEmpty()
        val email = binding.emailInput.text?.toString()?.trim().orEmpty()
        if (name.isBlank() || username.isBlank() || email.isBlank()) {
            binding.statusText.setText(R.string.complete_all_fields)
            return@launch
        }
        try {
            val response = RetrofitClient.api(this@AccountSettingsActivity)
                .updateProfile(ProfileUpdate(name, username, email))
            if (response.code() == 401) return@launch AuthGuard.redirectToLogin(this@AccountSettingsActivity)
            binding.statusText.text = if (response.isSuccessful) getString(R.string.profile_updated)
            else response.errorBody()?.string().orEmpty()
            if (response.isSuccessful) loadActivityLog()
        } catch (_: Exception) {
            binding.statusText.setText(R.string.connection_error)
        }
    }

    private fun changePassword() = lifecycleScope.launch {
        val current = binding.currentPasswordInput.text?.toString().orEmpty()
        val next = binding.newPasswordInput.text?.toString().orEmpty()
        if (current.isBlank() || next.length < 8) {
            binding.statusText.setText(R.string.password_requirements)
            return@launch
        }
        try {
            val response = RetrofitClient.api(this@AccountSettingsActivity)
                .changePassword(PasswordChange(current, next))
            if (response.code() == 401) return@launch AuthGuard.redirectToLogin(this@AccountSettingsActivity)
            binding.statusText.text = if (response.isSuccessful) getString(R.string.password_changed)
            else response.errorBody()?.string().orEmpty()
            if (response.isSuccessful) {
                binding.currentPasswordInput.text?.clear()
                binding.newPasswordInput.text?.clear()
                loadActivityLog()
            }
        } catch (_: Exception) {
            binding.statusText.setText(R.string.connection_error)
        }
    }

    private fun loadActivityLog() = lifecycleScope.launch {
        try {
            val response = RetrofitClient.api(this@AccountSettingsActivity).activityLog()
            if (response.code() == 401) return@launch AuthGuard.redirectToLogin(this@AccountSettingsActivity)
            allActivityLogs = response.body().orEmpty()
            currentLogPage = 1
            renderActivityLogPage()
        } catch (_: Exception) {
            binding.activityText.setText(R.string.connection_error)
            binding.logPaginationLayout.visibility = View.GONE
            binding.logPageIndicator.visibility = View.GONE
        }
    }

    private fun renderActivityLogPage() {
        if (allActivityLogs.isEmpty()) {
            binding.activityText.text = getString(R.string.activity_log_empty)
            binding.logPaginationLayout.visibility = View.GONE
            binding.logPageIndicator.visibility = View.GONE
            return
        }

        val totalPages = (allActivityLogs.size + logsPerPage - 1) / logsPerPage
        currentLogPage = currentLogPage.coerceIn(1, totalPages)

        val startIndex = (currentLogPage - 1) * logsPerPage
        val endIndex = (startIndex + logsPerPage).coerceAtMost(allActivityLogs.size)
        val pageItems = allActivityLogs.subList(startIndex, endIndex)

        binding.activityText.text = pageItems.mapIndexed { index, it ->
            val itemNumber = startIndex + index + 1
            val title = it.action.lowercase().replace('_', ' ').replaceFirstChar(Char::uppercase)
            val details = it.detail?.replace("; ", "\n")?.replace("network_location=", "IP / network location: ")?.replace("device=", "Device: ")
            listOfNotNull("$itemNumber. $title", it.createdAt.replace('T', ' '), details).joinToString("\n")
        }.joinToString("\n\n")

        binding.logPageText.text = getString(R.string.page_indicator, currentLogPage, totalPages)
        binding.logPageIndicator.text = getString(R.string.page_indicator, currentLogPage, totalPages)

        val showPagination = totalPages > 1
        binding.logPaginationLayout.visibility = if (showPagination) View.VISIBLE else View.GONE
        binding.logPageIndicator.visibility = if (showPagination) View.VISIBLE else View.GONE
        binding.prevLogPageButton.isEnabled = currentLogPage > 1
        binding.nextLogPageButton.isEnabled = currentLogPage < totalPages
    }

    private fun confirmDelete() {
        val dialogBinding = DialogDeleteAccountBinding.inflate(layoutInflater)
        val dialog = MaterialAlertDialogBuilder(this)
            .setView(dialogBinding.root)
            .create()

        dialogBinding.confirmationInput.doAfterTextChanged {
            val matches = it?.toString() == DELETE_CONFIRMATION
            dialogBinding.deleteButton.isEnabled = matches
            dialogBinding.confirmationInputLayout.error = null
        }
        dialogBinding.cancelButton.setOnClickListener { dialog.dismiss() }
        dialogBinding.deleteButton.setOnClickListener {
            dialog.dismiss()
            deleteAccount(DELETE_CONFIRMATION)
        }

        dialog.setOnShowListener {
            dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        }
        dialog.show()
    }

    private fun deleteAccount(confirmation: String) = lifecycleScope.launch {
        try {
            val response = RetrofitClient.api(this@AccountSettingsActivity)
                .deleteAccount(DeleteAccountRequest(confirmation))
            if (response.code() == 401) return@launch AuthGuard.redirectToLogin(this@AccountSettingsActivity)
            if (response.isSuccessful) {
                BatchHistoryStore.clear(this@AccountSettingsActivity)
                SessionManager(this@AccountSettingsActivity).clear()
                Toast.makeText(this@AccountSettingsActivity, R.string.account_deleted, Toast.LENGTH_LONG).show()
                startActivity(Intent(this@AccountSettingsActivity, LoginActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
                finish()
            } else binding.statusText.text = response.errorBody()?.string().orEmpty()
        } catch (_: Exception) {
            binding.statusText.setText(R.string.connection_error)
        }
    }

    companion object {
        private const val DELETE_CONFIRMATION = "DELETE ACCOUNT"
    }
}
