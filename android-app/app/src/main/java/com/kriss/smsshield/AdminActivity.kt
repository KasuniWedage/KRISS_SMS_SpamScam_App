package com.kriss.smsshield

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityAdminBinding
import com.kriss.smsshield.model.AdminUserItem
import com.kriss.smsshield.model.BackupFileInfo
import com.kriss.smsshield.storage.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.roundToInt

class AdminActivity : AppCompatActivity() {

    private lateinit var b: ActivityAdminBinding
    private var availableBackups: List<BackupFileInfo> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (SessionManager(this).role() != "admin") {
            Toast.makeText(this, "Administrator privileges required", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        b = ActivityAdminBinding.inflate(layoutInflater)
        setContentView(b.root)

        b.btnBack.setOnClickListener {
            if (isTaskRoot) {
                startActivity(Intent(this, HomeActivity::class.java))
            }
            finish()
        }
        b.swipeRefresh.setOnRefreshListener { loadAllData() }
        b.btnRefreshAll.setOnClickListener { loadAllData() }

        b.tvErrorLogs.setOnClickListener {
            MaterialAlertDialogBuilder(this)
                .setTitle("Clear System Error Logs")
                .setMessage("Do you want to clear the historical error telemetry log from the database?")
                .setPositiveButton("Clear Logs") { _, _ ->
                    lifecycleScope.launch {
                        try {
                            val resp = RetrofitClient.api(this@AdminActivity).clearAdminErrors()
                            if (resp.isSuccessful) {
                                Toast.makeText(this@AdminActivity, "Error telemetry logs cleared", Toast.LENGTH_SHORT).show()
                                loadAllData()
                            }
                        } catch (_: Exception) {
                            Toast.makeText(this@AdminActivity, "Failed to clear error logs", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        b.btnVerifyAudit.setOnClickListener { verifyAuditChain() }
        b.btnTriggerBackup.setOnClickListener { triggerDatabaseBackup() }
        b.btnRestoreTest.setOnClickListener { openBackupSelectionDialog() }
        b.btnDatasetManagement.setOnClickListener {
            startActivity(Intent(this, DatasetAdminActivity::class.java))
        }

        b.btnOpenHome.setOnClickListener {
            startActivity(Intent(this, HomeActivity::class.java))
        }

        b.btnLogout.setOnClickListener {
            SessionManager(this).clear()
            val intent = Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            startActivity(intent)
            finish()
        }

        loadAllData()
    }

    private fun loadAllData() {
        b.swipeRefresh.isRefreshing = true
        b.tvSystemStatus.text = "Refreshing telemetry..."

        lifecycleScope.launch {
            try {
                val api = RetrofitClient.api(this@AdminActivity)

                // 1. Fetch Metrics
                val metricsResp = api.adminMetrics()
                if (metricsResp.code() == 401 || metricsResp.code() == 403) {
                    AuthGuard.redirectToLogin(this@AdminActivity)
                    return@launch
                }
                val metrics = metricsResp.body()
                if (metrics != null) {
                    b.tvTotalUsers.text = metrics.users.toString()
                    b.tvTotalMessages.text = metrics.messages.toString()
                    b.tvTotalReports.text = metrics.reports.toString()

                    val legitCount = metrics.classifications["Legitimate"] ?: 0
                    val spamCount = metrics.classifications["Spam"] ?: 0
                    val scamCount = metrics.classifications["Scam"] ?: 0
                    val totalClass = (legitCount + spamCount + scamCount).coerceAtLeast(1)

                    b.tvLegitCount.text = legitCount.toString()
                    b.tvSpamCount.text = spamCount.toString()
                    b.tvScamCount.text = scamCount.toString()

                    b.pbLegit.progress = ((legitCount.toDouble() / totalClass) * 100).roundToInt()
                    b.pbSpam.progress = ((spamCount.toDouble() / totalClass) * 100).roundToInt()
                    b.pbScam.progress = ((scamCount.toDouble() / totalClass) * 100).roundToInt()
                }

                // 2. Fetch 24-Hour Performance
                val perfResp = api.adminPerformance(24)
                val perf = perfResp.body()
                if (perf != null) {
                    b.tvP95Latency.text = String.format(Locale.US, "%.1f ms", perf.latencyMs.p95)
                    b.tvSlaStatus.text = String.format(Locale.US, "SLA <2s: %.1f%%", perf.classification.within2SecondsPercent)
                    b.tvPerformanceDetail.text = String.format(
                        Locale.US,
                        "• 24h Request Volume: %d\n• Server Errors: %d (%.2f%% error rate)\n• Average Response Time: %.2f ms\n• P95 Latency: %.2f ms\n• Inference ≤2.0s Compliance: %.2f%%",
                        perf.requests,
                        perf.serverErrors,
                        perf.errorRatePercent,
                        perf.latencyMs.average,
                        perf.latencyMs.p95,
                        perf.classification.within2SecondsPercent
                    )
                }

                // 3. Fetch Audit Integrity
                val auditResp = api.auditIntegrity()
                val audit = auditResp.body()
                if (audit != null) {
                    updateAuditUI(audit.valid, audit.checked, audit.headHash, audit.reason)
                }

                // 4. Fetch Users List
                val usersResp = api.adminUsers()
                val users = usersResp.body().orEmpty()
                renderUsersList(users)

                // 5. Fetch Backups List
                val backupsResp = api.listBackups()
                availableBackups = backupsResp.body().orEmpty()
                if (availableBackups.isNotEmpty()) {
                    val latest = availableBackups.first()
                    b.tvBackupOutput.text = "Available Backups: ${availableBackups.size}\nLatest: ${latest.filename} (${latest.sizeKb} KB) on ${latest.createdAt}"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_secondary))
                } else {
                    b.tvBackupOutput.text = "No backup snapshots created yet. Tap 'Create Backup' to generate your first snapshot."
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_hint))
                }

                // 6. Fetch Errors
                val errorResp = api.adminErrors(10)
                val errors = errorResp.body().orEmpty()
                if (errors.isEmpty()) {
                    b.tvErrorLogs.text = "✅ Zero active errors. System is healthy and operating within SLA."
                    b.tvErrorLogs.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_secondary))
                } else {
                    val sb = StringBuilder()
                    errors.take(5).forEach { err ->
                        sb.append("⚠️ [${err.method ?: "GET"} ${err.path ?: "/"}] ${err.errorType ?: "Error"}: ${err.message ?: ""}\n")
                    }
                    b.tvErrorLogs.text = sb.toString().trim()
                    b.tvErrorLogs.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
                }

                // Update Header Status
                val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                b.tvSystemStatus.text = "System Status: Connected & Operational"
                b.tvLastUpdated.text = "Updated: " + timeFormat.format(Date())
                b.ivSystemDot.setImageResource(R.drawable.bg_circle_success)

            } catch (e: Exception) {
                b.tvSystemStatus.text = "Connection Error"
                b.ivSystemDot.setImageResource(R.drawable.bg_circle_danger)
                Toast.makeText(this@AdminActivity, "Failed to load telemetry: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            } finally {
                b.swipeRefresh.isRefreshing = false
            }
        }
    }

    private fun updateAuditUI(valid: Boolean, checked: Int, headHash: String?, reason: String?) {
        if (valid) {
            b.tvAuditStatus.text = "Cryptographic Chain Verified (SHA-256)"
            b.tvAuditStatus.setTextColor(ContextCompat.getColor(this, R.color.success))
            val hashSnippet = if (!headHash.isNullOrBlank() && headHash.length > 24) {
                headHash.substring(0, 24) + "..."
            } else {
                headHash ?: "None"
            }
            b.tvAuditDetail.text = "• Checked Sealed Logs: $checked\n• Head Record Hash: $hashSnippet\n• Integrity Status: Valid & Untampered"
        } else {
            b.tvAuditStatus.text = "Integrity Warning: Chain Inconsistency"
            b.tvAuditStatus.setTextColor(ContextCompat.getColor(this, R.color.danger))
            b.tvAuditDetail.text = "• Checked Logs: $checked\n• Violation Reason: ${reason ?: "Hash Mismatch"}"
        }
    }

    private fun verifyAuditChain() {
        b.btnVerifyAudit.isEnabled = false
        b.btnVerifyAudit.text = "Verifying..."

        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@AdminActivity).auditIntegrity()
                val audit = resp.body()
                if (audit != null) {
                    updateAuditUI(audit.valid, audit.checked, audit.headHash, audit.reason)
                    if (audit.valid) {
                        Toast.makeText(this@AdminActivity, "Cryptographic audit chain verified successfully!", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this@AdminActivity, "Warning: Tampering or hash mismatch detected!", Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(this@AdminActivity, "Verification failed: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            } finally {
                b.btnVerifyAudit.isEnabled = true
                b.btnVerifyAudit.text = "Verify Cryptographic Chain"
            }
        }
    }

    private fun triggerDatabaseBackup() {
        b.btnTriggerBackup.isEnabled = false
        b.btnTriggerBackup.text = "Creating..."

        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@AdminActivity).triggerBackup()
                if (resp.isSuccessful && resp.body() != null) {
                    val backup = resp.body()!!
                    val sizeKb = backup.sizeBytes / 1024
                    b.tvBackupOutput.text = "✅ Snapshot Created: ${backup.backupFile} (${sizeKb} KB)"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.success))
                    Toast.makeText(this@AdminActivity, "Backup created: ${backup.backupFile}", Toast.LENGTH_LONG).show()
                    loadAllData()
                } else {
                    b.tvBackupOutput.text = "❌ Backup trigger failed"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
                }
            } catch (e: Exception) {
                b.tvBackupOutput.text = "❌ Error: ${e.localizedMessage}"
                b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
            } finally {
                b.btnTriggerBackup.isEnabled = true
                b.btnTriggerBackup.text = "Create Backup"
            }
        }
    }

    private fun openBackupSelectionDialog() {
        if (availableBackups.isEmpty()) {
            MaterialAlertDialogBuilder(this)
                .setTitle("No Backups Found")
                .setMessage("No database backup files exist yet. Would you like to create a new backup snapshot now?")
                .setPositiveButton("Create Backup Now") { _, _ ->
                    triggerDatabaseBackup()
                }
                .setNegativeButton("Cancel", null)
                .show()
            return
        }

        val items = availableBackups.map { backup ->
            "${backup.filename}\n(${backup.sizeKb} KB • ${backup.createdAt})"
        }.toTypedArray()

        MaterialAlertDialogBuilder(this)
            .setTitle("Select Backup File to Restore")
            .setItems(items) { _, which ->
                val selectedBackup = availableBackups[which]
                showBackupActionDialog(selectedBackup)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showBackupActionDialog(backup: BackupFileInfo) {
        val options = arrayOf(
            "🧪 Run Sandbox Smoke Test (Safe & Isolated)",
            "⚡ Restore to Live Production Database"
        )

        MaterialAlertDialogBuilder(this)
            .setTitle("Target: ${backup.filename}")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> runSandboxRestoreTest(backup.filename)
                    1 -> confirmLiveRestore(backup.filename)
                }
            }
            .setNegativeButton("Back", null)
            .show()
    }

    private fun runSandboxRestoreTest(filename: String) {
        b.tvBackupOutput.text = "Testing sandbox restore on $filename..."
        b.tvBackupOutput.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))

        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@AdminActivity).triggerRestoreTest(filename)
                if (resp.isSuccessful && resp.body() != null) {
                    val result = resp.body()!!
                    val status = result["restoration_status"] as? String ?: ""
                    val passed = result["smoke_tests_passed"] as? Boolean ?: (result["valid"] as? Boolean ?: false)
                    val details = result["details"] as? Map<*, *>

                    if (passed || status == "SUCCESS") {
                        val rowCounts = details?.get("row_counts")?.toString() ?: "verified"
                        b.tvBackupOutput.text = "✅ Sandbox Restore Passed on $filename!\n• Status: SUCCESS\n• Row counts: $rowCounts\n• Zero impact on live database."
                        b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.success))
                        Toast.makeText(this@AdminActivity, "Sandbox restore passed for $filename!", Toast.LENGTH_SHORT).show()
                    } else {
                        b.tvBackupOutput.text = "❌ Sandbox Restore Failed for $filename"
                        b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
                    }
                } else {
                    b.tvBackupOutput.text = "❌ Restore test failed on server"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
                }
            } catch (e: Exception) {
                b.tvBackupOutput.text = "❌ Restore test error: ${e.localizedMessage}"
                b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
            }
        }
    }

    private fun confirmLiveRestore(filename: String) {
        MaterialAlertDialogBuilder(this)
            .setTitle("⚠️ Confirm Live Database Restore")
            .setMessage("Are you sure you want to restore the live database from '$filename'?\n\nThis will replace the current active database state with data from this snapshot.")
            .setPositiveButton("Yes, Restore Now") { _, _ ->
                executeLiveRestore(filename)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun executeLiveRestore(filename: String) {
        b.tvBackupOutput.text = "Executing live restoration from $filename..."
        b.tvBackupOutput.setTextColor(ContextCompat.getColor(this, R.color.warning))

        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@AdminActivity).triggerRestoreLive(filename)
                if (resp.isSuccessful && resp.body() != null) {
                    val result = resp.body()!!
                    val msg = result["message"] as? String ?: "Database restored successfully"
                    b.tvBackupOutput.text = "✅ $msg"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.success))
                    Toast.makeText(this@AdminActivity, "Live restore completed!", Toast.LENGTH_LONG).show()
                    loadAllData()
                } else {
                    b.tvBackupOutput.text = "❌ Live restoration failed"
                    b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
                }
            } catch (e: Exception) {
                b.tvBackupOutput.text = "❌ Live restore error: ${e.localizedMessage}"
                b.tvBackupOutput.setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.danger))
            }
        }
    }

    private fun renderUsersList(users: List<AdminUserItem>) {
        b.containerUsers.removeAllViews()
        b.tvUserCountBadge.text = "${users.size} users"

        if (users.isEmpty()) {
            val emptyTv = TextView(this).apply {
                text = "No registered users found"
                setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_secondary))
                textSize = 12f
            }
            b.containerUsers.addView(emptyTv)
            return
        }

        users.forEach { user ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                isClickable = true
                isFocusable = true
                setBackgroundResource(R.drawable.bg_field_outline)
                setOnClickListener { showUserManagementDialog(user) }
            }

            val avatar = TextView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    (36 * resources.displayMetrics.density).toInt(),
                    (36 * resources.displayMetrics.density).toInt()
                )
                text = (user.name.firstOrNull() ?: user.username.firstOrNull() ?: 'U').uppercase()
                gravity = Gravity.CENTER
                textSize = 14f
                setTypeface(null, android.graphics.Typeface.BOLD)
                if (user.role == "admin") {
                    setTextColor(Color.WHITE)
                    background = ContextCompat.getDrawable(this@AdminActivity, R.drawable.bg_circle_primary)
                } else {
                    setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.primary))
                    background = ContextCompat.getDrawable(this@AdminActivity, R.drawable.bg_chip_neutral)
                }
            }

            val info = LinearLayout(this).apply {
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                orientation = LinearLayout.VERTICAL
                setPadding((12 * resources.displayMetrics.density).toInt(), 0, (8 * resources.displayMetrics.density).toInt(), 0)
            }

            val nameTv = TextView(this).apply {
                text = user.name.ifBlank { user.username }
                textSize = 13f
                setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_primary))
                setTypeface(null, android.graphics.Typeface.BOLD)
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.END
            }

            val emailTv = TextView(this).apply {
                text = "@${user.username} • ${user.email}"
                textSize = 11.5f
                setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_secondary))
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.END
            }

            info.addView(nameTv)
            info.addView(emailTv)

            val roleBadge = TextView(this).apply {
                text = user.role.uppercase()
                textSize = 10.5f
                setTypeface(null, android.graphics.Typeface.BOLD)
                setPadding(
                    (10 * resources.displayMetrics.density).toInt(),
                    (4 * resources.displayMetrics.density).toInt(),
                    (10 * resources.displayMetrics.density).toInt(),
                    (4 * resources.displayMetrics.density).toInt()
                )
                if (user.role == "admin") {
                    background = ContextCompat.getDrawable(this@AdminActivity, R.drawable.bg_pill_info)
                    setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.primary))
                } else {
                    background = ContextCompat.getDrawable(this@AdminActivity, R.drawable.bg_field_outline)
                    setTextColor(ContextCompat.getColor(this@AdminActivity, R.color.text_secondary))
                }
            }

            row.addView(avatar)
            row.addView(info)
            row.addView(roleBadge)

            val marginParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, (4 * resources.displayMetrics.density).toInt(), 0, (4 * resources.displayMetrics.density).toInt())
            }
            row.layoutParams = marginParams
            row.setPadding(
                (12 * resources.displayMetrics.density).toInt(),
                (10 * resources.displayMetrics.density).toInt(),
                (12 * resources.displayMetrics.density).toInt(),
                (10 * resources.displayMetrics.density).toInt()
            )

            b.containerUsers.addView(row)
        }
    }

    private fun showUserManagementDialog(user: AdminUserItem) {
        val isTargetAdmin = user.role == "admin"
        val newRole = if (isTargetAdmin) "user" else "admin"
        val actionText = if (isTargetAdmin) "Demote to Standard User" else "Promote to Admin"

        MaterialAlertDialogBuilder(this)
            .setTitle("${user.name} (@${user.username})")
            .setMessage(
                "User ID: ${user.id}\n" +
                "Email: ${user.email}\n" +
                "Current Role: ${user.role.uppercase()}\n" +
                "Auth Provider: ${user.authProvider ?: "email"}\n" +
                "Language: ${user.languagePreference ?: "English"}"
            )
            .setPositiveButton(actionText) { _, _ ->
                updateUserRole(user.id, newRole)
            }
            .setNegativeButton("Close", null)
            .show()
    }

    private fun updateUserRole(userId: Int, newRole: String) {
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@AdminActivity).updateUserRole(userId, newRole)
                if (resp.isSuccessful) {
                    Toast.makeText(this@AdminActivity, "User role updated to $newRole!", Toast.LENGTH_SHORT).show()
                    loadAllData()
                } else {
                    Toast.makeText(this@AdminActivity, "Failed to update role", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@AdminActivity, "Error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
